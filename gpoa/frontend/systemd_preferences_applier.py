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
import binascii
import os
from pathlib import Path
import stat
import tempfile

from util.logging import log
from util.util import get_homedir, get_uid_by_username, string_to_literal_eval

from .applier_frontend import applier_frontend, check_enabled
from .appliers.systemd import (
    SystemdManager,
    SystemdManagerError,
    is_valid_unit_name,
)
from .change_journal import query, record_changed, record_presence_changed, watch_many
from gpt.systemds_constants import (
    DEFAULT_DROPIN_NAME,
    DROPIN_NAME_RE,
    MAX_DEPENDENCIES_PER_RULE,
    MAX_DEPENDENCY_PATH_LEN,
    MAX_UNIT_FILE_SIZE,
    NON_RESTARTABLE_TYPES,
    VALID_APPLY_MODES,
    VALID_DEP_MODES,
    VALID_POLICY_TARGETS,
    VALID_STATES,
)

MANAGED_HEADER = '# gpupdate-managed uid: {}'
MAX_RULES_PER_SCOPE = 512


class _Context:
    def __init__(self, mode='machine', username=None):
        self.mode = mode
        self.username = username
        self.systemd_dir = '/etc/systemd/system'
        if mode == 'user':
            self.systemd_dir = os.path.join(get_homedir(username), '.config/systemd/user')
        elif mode == 'global_user':
            self.systemd_dir = '/etc/systemd/user'


def _syslog(level, message, data=None):
    payload = {'plugin': 'SystemdPreferencesApplier', 'message': message}
    if data:
        payload['data'] = data
    log(level, payload)


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).lower() in ('1', 'true', 'yes')


def _has_control_chars(value):
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in str(value))


def _is_valid_dropin_name(value):
    if not isinstance(value, str):
        return False
    if not value or value != value.strip():
        return False
    if '\x00' in value or '/' in value or '\\' in value:
        return False
    if _has_control_chars(value):
        return False
    return bool(DROPIN_NAME_RE.match(value))


def _expand_windows_var(path, username=None):
    if not path:
        return path
    variables = {
        'HOME': '/etc/skel',
        'HOMEPATH': '/etc/skel',
        'HOMEDRIVE': '/',
        'SystemRoot': '/',
        'SystemDrive': '/',
        'USERNAME': username if username else '',
    }
    if username:
        variables['HOME'] = get_homedir(username)
        variables['HOMEPATH'] = variables['HOME']
    result = path
    for key, value in variables.items():
        replacement = str(value)
        if key not in ('USERNAME',) and not replacement.endswith('/'):
            replacement = '{}{}'.format(replacement, '/')
        result = result.replace('%{}%'.format(key), replacement)
    return result


def _read_preferences(storage, scope_name, is_previous=False):
    prefix = 'Software/BaseALT/Policies/Preferences/{}'.format(scope_name)
    if is_previous:
        prefix = 'Previous/{}'.format(prefix)
    key = '{}/Systemds'.format(prefix)
    value = storage.get_entry(key, preg=False)
    if not value:
        return []

    items = string_to_literal_eval(value)
    if not isinstance(items, list):
        return []
    entries = [item for item in items if isinstance(item, dict)]
    if len(entries) > MAX_RULES_PER_SCOPE:
        log('W47', {
            'reason': 'Systemd preferences rule limit exceeded',
            'scope': scope_name,
            'count': len(entries),
            'limit': MAX_RULES_PER_SCOPE,
        })
        return entries[:MAX_RULES_PER_SCOPE]
    return entries


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


def _derive_edit_mode(apply_mode):
    if apply_mode == 'always':
        return 'create_or_override'
    elif apply_mode == 'if_exists':
        return 'override'
    elif apply_mode == 'if_missing':
        return 'create'
    return 'create_or_override'


def _normalize_rule(item):
    unit = item.get('unit')
    state = item.get('state')
    apply_mode = item.get('apply_mode', item.get('applyMode', 'always'))
    policy_target = item.get('policy_target', item.get('policyTarget', 'machine'))
    uid = item.get('uid')

    if not unit or state not in VALID_STATES:
        return None
    if not is_valid_unit_name(str(unit)):
        log('W47', {'reason': 'Invalid unit value', 'unit': unit})
        return None
    if apply_mode not in VALID_APPLY_MODES:
        return None
    if policy_target not in VALID_POLICY_TARGETS:
        return None
    if not uid:
        return None

    dependencies = item.get('file_dependencies', item.get('fileDependencies', []))
    if not isinstance(dependencies, list):
        dependencies = []
    if len(dependencies) > MAX_DEPENDENCIES_PER_RULE:
        log('W47', {
            'reason': 'Too many file dependencies, truncating',
            'unit': unit,
            'count': len(dependencies),
            'limit': MAX_DEPENDENCIES_PER_RULE,
        })
        dependencies = dependencies[:MAX_DEPENDENCIES_PER_RULE]

    valid_dependencies = []
    for dep in dependencies:
        if not isinstance(dep, dict):
            continue
        mode = dep.get('mode')
        path = dep.get('path')
        if mode not in VALID_DEP_MODES or not path:
            continue
        if not _is_valid_dependency_path(str(path), policy_target):
            log('W47', {
                'reason': 'Invalid dependency path',
                'unit': unit,
                'path': str(path),
                'policy_target': policy_target,
            })
            continue
        valid_dependencies.append({'mode': mode, 'path': str(path)})

    dropin_name = item.get('dropin_name', item.get('dropInName', DEFAULT_DROPIN_NAME)) or DEFAULT_DROPIN_NAME
    if not _is_valid_dropin_name(str(dropin_name)):
        log('W47', {'reason': 'Invalid dropInName', 'dropInName': dropin_name, 'unit': unit})
        return None

    unit_file = _decode_unit_file_b64(item, unit, uid)
    if unit_file is None:
        unit_file = _normalize_unit_file_content(item.get('unit_file', item.get('unitFile')))
    if unit_file is None and (item.get('unit_file') is not None or item.get('unitFile') is not None):
        log('W47', {
            'reason': 'Invalid unit_file payload',
            'unit': unit,
            'uid': str(uid),
        })

    return {
        'uid': str(uid),
        'unit': str(unit),
        'state': state,
        'now': _as_bool(item.get('now', False)),
        'remove_policy': _as_bool(item.get('remove_policy', item.get('removePolicy', False))),
        'apply_mode': apply_mode,
        'policy_target': policy_target,
        'edit_mode': _derive_edit_mode(apply_mode),
        'dropin_name': str(dropin_name),
        'unit_file': unit_file,
        'file_dependencies': valid_dependencies,
        'element_type': item.get('element_type', item.get('elementType', 'service')),
    }


def _rule_matches_apply_mode(rule, exists):
    apply_mode = rule['apply_mode']
    if apply_mode == 'always':
        return True
    if apply_mode == 'if_exists':
        return exists
    return not exists


def _is_managed_by_uid(path, uid):
    if not path.exists() or not path.is_file():
        return False
    content = _safe_read_text(path)
    if content is None:
        return False
    first_line = content.splitlines()[0] if content else ''
    return first_line == MANAGED_HEADER.format(uid)


def _validate_existing_file(path):
    fd = None
    try:
        flags = os.O_RDONLY
        if hasattr(os, 'O_NOFOLLOW'):
            flags |= os.O_NOFOLLOW
        fd = os.open(str(path), flags)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return None, False
        if st.st_nlink > 1:
            return None, False
        with os.fdopen(fd, 'r', encoding='utf-8') as file_obj:
            content = file_obj.read()
            fd = None
            return content, True
    except (OSError, UnicodeDecodeError):
        return None, False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _safe_read_text(path):
    content, ok = _validate_existing_file(path)
    if not ok:
        return None
    return content


def _safe_write_text(path, content):
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    if parent.is_symlink():
        return False, False

    existed = path.exists()
    if existed:
        _, ok = _validate_existing_file(path)
        if not ok:
            return False, existed

    data = content.encode('utf-8')
    tmp_fd = None
    tmp_path = None
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(prefix='.gpupdate-', dir=str(parent))
        os.fchmod(tmp_fd, 0o644)
        os.write(tmp_fd, data)
        os.fsync(tmp_fd)
        os.close(tmp_fd)
        tmp_fd = None
        os.replace(tmp_path, str(path))
        tmp_path = None  # consumed by replace; prevent unlink in finally
    except OSError:
        return False, existed
    finally:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    try:
        dir_fd = os.open(str(parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass  # fsync failure is non-fatal; file is already atomically written

    return True, existed


def _normalize_unit_file_content(unit_file):
    if unit_file is None:
        return None

    text = str(unit_file)
    # Keep already multiline text as-is; only unescape policy-encoded newlines.
    if '\n' in text or '\r' in text:
        normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    elif '\\n' in text or '\\r' in text:
        normalized = text.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\r', '\n')
    else:
        normalized = text

    if len(normalized.encode('utf-8')) > MAX_UNIT_FILE_SIZE:
        return None
    return normalized


def _decode_unit_file_b64(item, unit, uid):
    payload = item.get('unit_file_b64', item.get('unitFileB64'))
    if payload is None:
        return None

    try:
        data = base64.b64decode(str(payload), validate=True)
        if len(data) > MAX_UNIT_FILE_SIZE:
            log('W47', {
                'reason': 'unit_file_b64 exceeds size limit',
                'unit': unit,
                'uid': uid,
                'limit': MAX_UNIT_FILE_SIZE,
            })
            return None
        return data.decode('utf-8')
    except (TypeError, ValueError, binascii.Error, UnicodeDecodeError):
        log('W47', {
            'reason': 'Invalid unit_file_b64 payload',
            'unit': unit,
            'uid': uid,
        })
        return None


class _systemd_preferences_runtime:
    def __init__(self, storage, scope_name, context, systemd_manager=None):
        self.storage = storage
        self.scope_name = scope_name
        self.context = context
        self.systemd_manager = systemd_manager
        self.daemon_reload_required = False
        self.phase2_candidates = []

    def _manager(self):
        if self.systemd_manager is None:
            try:
                self.systemd_manager = SystemdManager(mode=self.context.mode)
            except Exception as exc:
                raise SystemdManagerError(str(exc), action='connect')
        return self.systemd_manager

    def _exists(self, unit_name):
        try:
            return self._manager().exists(unit_name)
        except SystemdManagerError as exc:
            _syslog('W', 'Unable to query unit existence', {'unit': unit_name, 'error': str(exc)})
            return False

    def _daemon_reload(self):
        log('D245', {'context': self.context.mode})
        try:
            self._manager().reload()
        except SystemdManagerError as exc:
            error = str(exc)
            log('W50', {'context': self.context.mode, 'error': error})
            _syslog('W', 'daemon-reload failed', {'context': self.context.mode, 'error': error})
            self.daemon_reload_required = False
            return False
        self.daemon_reload_required = False
        return True

    def _active_state(self, unit_name):
        try:
            return self._manager().active_state(unit_name)
        except SystemdManagerError:
            return None

    def _stop(self, rule):
        if rule.get('element_type') in NON_RESTARTABLE_TYPES:
            return
        if self.context.mode == 'global_user':
            return
        state = self._active_state(rule['unit'])
        if state not in ('active', 'activating', 'deactivating'):
            return
        try:
            self._manager().stop(rule['unit'])
        except SystemdManagerError as exc:
            _syslog('W', 'Stop failed', {'unit': rule['unit'], 'error': str(exc)})

    def _restart(self, rule):
        if rule.get('element_type') in NON_RESTARTABLE_TYPES:
            log('W49', {'unit': rule['unit'], 'type': rule.get('element_type')})
            _syslog('D', 'Unit type is non-restartable', {'unit': rule['unit'], 'type': rule.get('element_type')})
            return

        if self.context.mode == 'global_user':
            _syslog('D', 'Dependency restart skipped: not supported for global_user scope',
                    {'unit': rule['unit']})
            return

        state = self._active_state(rule['unit'])
        if state not in ('active', 'activating'):
            return

        try:
            self._manager().restart(rule['unit'])
        except SystemdManagerError as exc:
            _syslog('W', 'Restart failed', {'unit': rule['unit'], 'error': str(exc)})

    def _rule_managed_paths(self, rule):
        unit_file_path = Path(self.context.systemd_dir).joinpath(rule['unit'])
        dropin_path = Path(self.context.systemd_dir).joinpath(
            '{}.d'.format(rule['unit']), rule['dropin_name'])
        return unit_file_path, dropin_path

    def _write_rule_file(self, target_file, uid, unit_file):
        marker = MANAGED_HEADER.format(uid)
        body = unit_file if unit_file.endswith('\n') else '{}\n'.format(unit_file)
        content = '{}\n{}'.format(marker, body)
        old_content = _safe_read_text(target_file) if target_file.exists() else None
        if old_content == content:
            return

        written, existed = _safe_write_text(target_file, content)
        if not written:
            _syslog('W', 'Unable to safely write managed file', {'path': str(target_file)})
            return

        if existed:
            record_changed(str(target_file))
        else:
            record_presence_changed(str(target_file))
        self.daemon_reload_required = True

    def _apply_edit(self, rule, exists):
        unit_file = rule.get('unit_file')
        if not unit_file:
            return

        unit_file_path, dropin_path = self._rule_managed_paths(rule)
        edit_mode = rule['edit_mode']
        if edit_mode == 'create':
            self._write_rule_file(unit_file_path, rule['uid'], unit_file)
            return
        if edit_mode == 'override':
            self._write_rule_file(dropin_path, rule['uid'], unit_file)
            return
        if exists:
            self._write_rule_file(dropin_path, rule['uid'], unit_file)
        else:
            self._write_rule_file(unit_file_path, rule['uid'], unit_file)

    def _run_state_action(self, rule):
        state = rule['state']
        if state == 'as_is':
            return

        try:
            self._manager().apply_state(rule['unit'], state, rule['now'])
        except (SystemdManagerError, ValueError) as exc:
            _syslog('W', 'State apply failed', {'unit': rule['unit'], 'state': state, 'error': str(exc)})

    def apply_rules(self, rules):
        applicable_rules = []
        for rule in rules:
            log('D244', {'unit': rule['unit'], 'state': rule['state']})
            exists = self._exists(rule['unit'])
            if not _rule_matches_apply_mode(rule, exists):
                # Rule does not qualify for edit/state this run, but should
                # still be checked for dependency-triggered restarts.
                self.phase2_candidates.append(rule)
                continue
            applicable_rules.append((rule, exists))

        for rule, exists in applicable_rules:
            self._apply_edit(rule, exists)

        if self.daemon_reload_required and not self._daemon_reload():
            _syslog('W', 'Skipping state apply due to daemon-reload failure', {
                'context': self.context.mode,
                'rules': len(applicable_rules),
            })
            return

        for rule, _ in applicable_rules:
            self._run_state_action(rule)
            self.phase2_candidates.append(rule)

    def cleanup_removed_rules(self, removed_rules):
        affected_units = set()
        for rule in removed_rules:
            log('D246', {'unit': rule['unit'], 'uid': rule['uid']})
            unit_file_path, dropin_path = self._rule_managed_paths(rule)
            for target in (unit_file_path, dropin_path):
                if not _is_managed_by_uid(target, rule['uid']):
                    continue
                try:
                    target.unlink()
                    record_presence_changed(str(target))
                    self.daemon_reload_required = True
                    affected_units.add((rule['unit'], rule.get('element_type', 'service')))
                except Exception as exc:
                    _syslog('W', 'Failed to cleanup managed file', {'path': str(target), 'error': str(exc)})
            dropin_dir = dropin_path.parent
            if dropin_dir.exists():
                try:
                    dropin_dir.rmdir()
                except OSError:
                    pass

        if self.daemon_reload_required:
            if not self._daemon_reload():
                _syslog('W', 'Skipping cleanup restart due to daemon-reload failure', {
                    'context': self.context.mode,
                    'units': [unit_name for unit_name, _ in affected_units],
                })
                return
            for unit_name, element_type in affected_units:
                cleanup_rule = {
                    'unit': unit_name,
                    'element_type': element_type,
                }
                self._stop(cleanup_rule)

    def _dependency_changed(self, dependency, username=None):
        dep_path = _expand_windows_var(dependency['path'], username)
        if not dep_path or not os.path.isabs(dep_path):
            return False
        mode = dependency['mode']
        return query(dep_path, mode=mode)

    def post_restart(self, username=None):
        for rule in self.phase2_candidates:
            dependencies = rule.get('file_dependencies', [])
            if not dependencies:
                continue
            if any(self._dependency_changed(dep, username=username) for dep in dependencies):
                log('D247', {'unit': rule['unit']})
                self._restart(rule)


def _get_removed_rules(storage, scope_name, target):
    current_raw = _read_preferences(storage, scope_name, is_previous=False)
    previous_raw = _read_preferences(storage, scope_name, is_previous=True)
    current_map = {}
    previous_map = {}
    for item in current_raw:
        normalized = _normalize_rule(item)
        if normalized is not None and normalized['policy_target'] == target:
            current_map[normalized['uid']] = normalized
    for item in previous_raw:
        normalized = _normalize_rule(item)
        if normalized is not None and normalized['policy_target'] == target:
            previous_map[normalized['uid']] = normalized
    removed_uids = set(previous_map.keys()) - set(current_map.keys())
    return [previous_map[uid] for uid in removed_uids]


def _get_rules_for_scope(storage, scope_name, target):
    current_raw = _read_preferences(storage, scope_name, is_previous=False)
    rules = []
    for item in current_raw:
        normalized = _normalize_rule(item)
        if normalized is None:
            continue
        if normalized['policy_target'] != target:
            continue
        rules.append(normalized)
    return rules


def _split_active_and_cleanup_rules(rules):
    active_rules = []
    explicit_cleanup_rules = []
    for rule in rules:
        if rule.get('remove_policy'):
            explicit_cleanup_rules.append(rule)
            continue
        active_rules.append(rule)
    return active_rules, explicit_cleanup_rules


def _merge_cleanup_rules(removed_by_diff, explicit_cleanup_rules):
    merged = {}
    for rule in removed_by_diff:
        merged[rule['uid']] = rule
    for rule in explicit_cleanup_rules:
        merged[rule['uid']] = rule
    return list(merged.values())


def _get_rule_sets_for_scope(storage, scope_name, target):
    current_rules = _get_rules_for_scope(storage, scope_name, target)
    active_rules, explicit_cleanup_rules = _split_active_and_cleanup_rules(current_rules)
    removed_by_diff = _get_removed_rules(storage, scope_name, target)
    cleanup_rules = _merge_cleanup_rules(removed_by_diff, explicit_cleanup_rules)
    return active_rules, cleanup_rules


def _collect_dependency_paths(storage, scope_name, target, username=None):
    dependency_paths = []
    for rule in _get_rules_for_scope(storage, scope_name, target):
        if rule.get('remove_policy'):
            continue
        for dependency in rule.get('file_dependencies', []):
            dep_path = _expand_windows_var(dependency.get('path'), username)
            if dep_path and os.path.isabs(dep_path):
                dependency_paths.append(dep_path)
    return dependency_paths


class systemd_preferences_applier(applier_frontend):
    __module_name = 'SystemdPreferencesApplier'
    __module_experimental = True
    __module_enabled = False
    __scope_name = 'Machine'

    def __init__(self, storage):
        self.storage = storage
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def prime_dependency_journal(self):
        if not self.__module_enabled:
            return
        dependency_paths = []
        dependency_paths.extend(_collect_dependency_paths(self.storage, self.__scope_name, target='machine'))
        dependency_paths.extend(_collect_dependency_paths(self.storage, self.__scope_name, target='user'))
        watch_many(dependency_paths)

    def apply(self):
        if not self.__module_enabled:
            log('D243')
            return

        log('D240')
        runtime = _systemd_preferences_runtime(self.storage, self.__scope_name, _Context(mode='machine'))
        active_rules, cleanup_rules = _get_rule_sets_for_scope(
            self.storage, self.__scope_name, target='machine')
        runtime.apply_rules(active_rules)
        runtime.cleanup_removed_rules(cleanup_rules)
        runtime.post_restart()

        global_user_runtime = _systemd_preferences_runtime(
            self.storage,
            self.__scope_name,
            _Context(mode='global_user'),
        )
        active_user_rules, cleanup_user_rules = _get_rule_sets_for_scope(
            self.storage,
            self.__scope_name,
            target='user',
        )
        global_user_runtime.apply_rules(active_user_rules)
        global_user_runtime.cleanup_removed_rules(cleanup_user_rules)
        global_user_runtime.post_restart()


class systemd_preferences_applier_user(applier_frontend):
    __module_name = 'SystemdPreferencesApplierUser'
    __module_experimental = True
    __module_enabled = False

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        self.uid = get_uid_by_username(username)
        self.user_bus_path = '/run/user/{}/bus'.format(self.uid) if self.uid is not None else None
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def prime_dependency_journal(self):
        if not self.__module_enabled:
            return

        dependency_paths = []
        dependency_paths.extend(_collect_dependency_paths(self.storage, self.username, target='machine'))
        dependency_paths.extend(_collect_dependency_paths(
            self.storage,
            self.username,
            target='user',
            username=self.username,
        ))
        watch_many(dependency_paths)

    def admin_context_apply(self):
        if not self.__module_enabled:
            log('D243')
            return

        log('D241', {'username': self.username})
        runtime = _systemd_preferences_runtime(self.storage, self.username, _Context(mode='machine'))
        active_rules, cleanup_rules = _get_rule_sets_for_scope(
            self.storage, self.username, target='machine')
        runtime.apply_rules(active_rules)
        runtime.cleanup_removed_rules(cleanup_rules)
        runtime.post_restart()

    def user_context_apply(self):
        if not self.__module_enabled:
            log('D243')
            return
        log('D242', {'username': self.username})
        if not self.user_bus_path or not os.path.exists(self.user_bus_path):
            log('W48', {'username': self.username, 'path': self.user_bus_path})
            _syslog('W', 'systemd --user manager is unavailable', {
                'username': self.username,
                'path': self.user_bus_path,
            })
            return

        runtime = _systemd_preferences_runtime(
            self.storage,
            self.username,
            _Context(mode='user', username=self.username))
        active_rules, cleanup_rules = _get_rule_sets_for_scope(
            self.storage, self.username, target='user')
        runtime.apply_rules(active_rules)
        runtime.cleanup_removed_rules(cleanup_rules)
        runtime.post_restart(username=self.username)
