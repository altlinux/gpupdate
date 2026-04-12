#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
import os
from xml.etree import ElementTree

from util.logging import log

from .dynamic_attributes import DynamicAttributes
from .systemds_constants import (
    DEFAULT_DROPIN_NAME,
    DROPIN_NAME_RE,
    MAX_DEPENDENCIES_PER_RULE,
    MAX_DEPENDENCY_PATH_LEN,
    MAX_UNIT_FILE_SIZE,
    UNIT_NAME_RE,
    VALID_APPLY_MODES,
    VALID_DEP_MODES,
    VALID_POLICY_TARGETS,
    VALID_STATES,
)


VALID_POLICY_ELEMENTS = {
    'Service',
    'Socket',
    'Timer',
    'Path',
    'Mount',
    'Automount',
    'Swap',
    'Target',
    'Device',
    'Slice',
    'Scope',
}

UNIT_SUFFIX = {
    'Service': '.service',
    'Socket': '.socket',
    'Timer': '.timer',
    'Path': '.path',
    'Mount': '.mount',
    'Automount': '.automount',
    'Swap': '.swap',
    'Target': '.target',
    'Device': '.device',
    'Slice': '.slice',
    'Scope': '.scope',
}


def _tag_name(element):
    return str(element.tag).split('}')[-1]


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).lower() in ('1', 'true', 'yes')


def _normalize_unit_name(unit_name, element_name):
    if not unit_name:
        return None

    all_suffixes = set(UNIT_SUFFIX.values())
    if any(str(unit_name).endswith(suffix) for suffix in all_suffixes):
        return unit_name

    suffix = UNIT_SUFFIX.get(element_name)
    if not suffix:
        return unit_name

    return '{}{}'.format(unit_name, suffix)


def _is_safe_component(value):
    text = str(value) if value is not None else ''
    if not text:
        return False
    if text in ('.', '..'):
        return False
    if text != text.strip():
        return False
    if '/' in text or '\\' in text:
        return False
    if os.path.isabs(text):
        return False
    if len(text) >= 2 and text[1] == ':' and text[0].isalpha():
        return False
    if '\x00' in text:
        return False
    return True


def _has_control_chars(value):
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in str(value))


def _derive_edit_mode(apply_mode):
    if apply_mode == 'always':
        return 'create_or_override'
    elif apply_mode == 'if_exists':
        return 'override'
    elif apply_mode == 'if_missing':
        return 'create'
    return 'create_or_override'


def _is_valid_unit_name(value):
    if not _is_safe_component(value):
        return False
    if _has_control_chars(value):
        return False
    if not UNIT_NAME_RE.match(str(value)):
        return False
    name_part = str(value).rsplit('.', 1)[0]
    if name_part.startswith('-') or name_part.endswith('-'):
        return False
    return True


def _is_valid_dropin_name(value):
    if not _is_safe_component(value):
        return False
    if _has_control_chars(value):
        return False
    return bool(DROPIN_NAME_RE.match(str(value)))


def _expand_windows_var(path):
    if not path:
        return path
    variables = {
        'HOME': '/etc/skel',
        'HOMEPATH': '/etc/skel',
        'HOMEDRIVE': '/',
        'SystemRoot': '/',
        'SystemDrive': '/',
        'USERNAME': '',
    }
    result = str(path)
    for key, value in variables.items():
        replacement = str(value)
        if key not in ('USERNAME',) and not replacement.endswith('/'):
            replacement = '{}{}'.format(replacement, '/')
        result = result.replace('%{}%'.format(key), replacement)
    return result


def _is_valid_dependency_path(path, policy_target):
    if not isinstance(path, str):
        return False
    if not path or len(path) > MAX_DEPENDENCY_PATH_LEN:
        return False
    if '\x00' in path or _has_control_chars(path):
        return False

    expanded = _expand_windows_var(path)
    if not expanded or len(expanded) > MAX_DEPENDENCY_PATH_LEN:
        return False
    if '\x00' in expanded or _has_control_chars(expanded):
        return False

    upper_path = path.upper()
    if policy_target == 'user':
        if '%HOME%' in upper_path or '%HOMEPATH%' in upper_path:
            return os.path.isabs(expanded)
        return os.path.isabs(path) and os.path.isabs(expanded)

    return os.path.isabs(expanded)


def _get_systemds_root(systemds_file):
    try:
        from defusedxml import ElementTree as DefusedElementTree
        xml_contents = DefusedElementTree.parse(systemds_file)
    except ImportError:
        log('W47', {'reason': 'defusedxml is unavailable, using xml.etree fallback'})
        xml_contents = ElementTree.parse(systemds_file)
    return xml_contents.getroot()


def _invalid_entry(message, data=None):
    payload = {'reason': message}
    if data:
        payload.update(data)
    log('W47', payload)


def _parse_file_dependencies(properties, policy_target, unit):
    file_dependencies = []
    dependencies = properties.find('FileDependencies')
    if dependencies is None:
        return file_dependencies

    dependency_items = list(dependencies.findall('Dependency'))
    if len(dependency_items) > MAX_DEPENDENCIES_PER_RULE:
        _invalid_entry('Too many dependency entries, truncating', {
            'unit': unit,
            'count': len(dependency_items),
            'limit': MAX_DEPENDENCIES_PER_RULE,
        })
        dependency_items = dependency_items[:MAX_DEPENDENCIES_PER_RULE]

    for dependency in dependency_items:
        mode = dependency.get('mode')
        path = dependency.get('path')
        if mode not in VALID_DEP_MODES or not path:
            _invalid_entry('Invalid dependency entry', {'mode': mode, 'path': path})
            continue
        if not _is_valid_dependency_path(str(path), policy_target):
            _invalid_entry('Invalid dependency path', {
                'mode': mode,
                'path': path,
                'policy_target': policy_target,
                'unit': unit,
            })
            continue
        file_dependencies.append({'mode': mode, 'path': path})

    return file_dependencies


def _parse_policy_element(policy_element):
    element_name = _tag_name(policy_element)
    if element_name not in VALID_POLICY_ELEMENTS:
        return None

    properties = policy_element.find('Properties')
    if properties is None:
        _invalid_entry('Missing <Properties> in Systemds element', {'element': element_name})
        return None

    unit = _normalize_unit_name(properties.get('unit'), element_name)
    state = properties.get('state')
    apply_mode = properties.get('applyMode', 'always')
    policy_target = properties.get('policyTarget', 'machine')

    if not unit:
        _invalid_entry('Missing unit attribute', {'element': element_name})
        return None
    if not _is_valid_unit_name(unit):
        _invalid_entry('Invalid unit value', {'element': element_name, 'unit': unit})
        return None
    if state not in VALID_STATES:
        _invalid_entry('Invalid state', {'element': element_name, 'state': state, 'unit': unit})
        return None
    if apply_mode not in VALID_APPLY_MODES:
        _invalid_entry('Invalid applyMode', {'element': element_name, 'apply_mode': apply_mode, 'unit': unit})
        return None
    if policy_target not in VALID_POLICY_TARGETS:
        _invalid_entry('Invalid policyTarget', {'element': element_name, 'policy_target': policy_target, 'unit': unit})
        return None
    uid = policy_element.get('uid')
    clsid = policy_element.get('clsid')
    name = policy_element.get('name')
    if not uid or not clsid or not name:
        _invalid_entry('Missing required policy attributes', {
            'element': element_name,
            'uid': uid,
            'clsid': clsid,
            'name': name,
            'unit': unit,
        })
        return None

    unit_file = properties.find('UnitFile')
    unit_file_text = None
    unit_file_b64 = None
    if unit_file is not None and unit_file.text is not None:
        # UnitFile mode=table is treated as plain text by design.
        unit_file_text = str(unit_file.text)
        if len(unit_file_text.encode('utf-8')) > MAX_UNIT_FILE_SIZE:
            _invalid_entry('UnitFile exceeds size limit', {
                'element': element_name,
                'unit': unit,
                'limit': MAX_UNIT_FILE_SIZE,
            })
            return None
        unit_file_b64 = base64.b64encode(unit_file_text.encode('utf-8')).decode('ascii')

    policy = systemd_policy(unit)
    policy.element_type = element_name.lower()
    policy.clsid = clsid
    policy.name = name
    policy.status = policy_element.get('status')
    policy.image = policy_element.get('image')
    policy.changed = policy_element.get('changed')
    policy.uid = uid
    policy.desc = policy_element.get('desc')
    policy.bypassErrors = policy_element.get('bypassErrors')
    policy.userContext = policy_element.get('userContext')
    policy.removePolicy = policy_element.get('removePolicy')

    policy.state = state
    policy.now = _as_bool(properties.get('now'), default=False)
    policy.apply_mode = apply_mode
    policy.policy_target = policy_target
    policy.edit_mode = _derive_edit_mode(apply_mode)
    dropin_name = properties.get('dropInName', DEFAULT_DROPIN_NAME) or DEFAULT_DROPIN_NAME
    if not _is_valid_dropin_name(dropin_name):
        _invalid_entry('Invalid dropInName', {'element': element_name, 'dropInName': dropin_name, 'unit': unit})
        return None

    policy.dropin_name = dropin_name
    policy.unit_file = unit_file_text
    policy.unit_file_b64 = unit_file_b64
    policy.unit_file_mode = 'text'
    policy.file_dependencies = _parse_file_dependencies(properties, policy_target, unit)

    return policy


def read_systemds(systemds_file):
    """
    Read Systemds.xml from GPT.
    """
    policies = []
    root = _get_systemds_root(systemds_file)
    if _tag_name(root) != 'Systemds':
        _invalid_entry('Unexpected root element in Systemds.xml', {'root': _tag_name(root)})
        return policies

    for policy_element in root:
        parsed = _parse_policy_element(policy_element)
        if parsed is not None:
            policies.append(parsed)

    return policies


def merge_systemds(storage, systemd_objects, policy_name):
    for systemd_object in systemd_objects:
        storage.add_systemd(systemd_object, policy_name)


class systemd_policy(DynamicAttributes):
    def __init__(self, unit):
        self.unit = unit
