#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#
# This program is free software: you may distribute it and/or modify
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

"""
GPP State Management Module.

Handles lifecycle state for GPP elements:
 - Tracking applied elements (for applyOnce)
 - Detecting removed elements (for removePolicy)
 - GPO unlink detection and cleanup
"""

from datetime import datetime
from typing import Dict, List, Set
from ast import literal_eval

from .dconf_registry import Dconf_registry
from util.logging import log


# Actions that should be skipped during cleanup
# (DELETE actions already perform cleanup during application)
CLEANUP_SKIP_ACTIONS = {'D', 'DELETE'}


def get_previous_elements(element_type: str, username: str = None) -> List[Dict]:
    '''
    Get previously stored GPP elements from dconf.

    :param element_type: Type of element ('Inifiles', 'Files', 'Folders', etc.)
    :param username: Username for user preferences, None for machine
    :return: List of element dictionaries
    '''
    if username is None or username == 'Machine':
        prefix = 'Previous/Software/BaseALT/Policies/Preferences/Machine'
    else:
        prefix = f'Previous/Software/BaseALT/Policies/Preferences/{username}'

    registry = Dconf_registry.get_storage()
    if prefix not in registry:
        return []

    elements_data = registry[prefix].get(element_type, [])
    if not elements_data:
        return []

    try:
        if isinstance(elements_data, str):
            elements = literal_eval(elements_data)
        else:
            elements = elements_data
        return elements if isinstance(elements, list) else []
    except Exception as e:
        logdata = {'element_type': element_type, 'error': str(e)}
        log('E74', logdata)
        return []


def find_removed_elements(
    current_elements: List[Dict],
    previous_elements: List[Dict],
    key_field: str = 'uid'
) -> List[Dict]:
    '''
    Find elements that existed previously but are no longer present.

    :param current_elements:Currently active elements
    :param previous_elements: Elements from previous gpupdate run
    :param key_field: Field to use for comparison (default: 'uid')
    :return: List of removed elements that have removePolicy=True
    '''
    current_uids = set()
    for elem in current_elements:
        uid = elem.get(key_field) or elem.get('uid')
        if uid:
            current_uids.add(uid)

    removed = []
    for prev_elem in previous_elements:
        uid = prev_elem.get(key_field) or prev_elem.get('uid')
        if uid and uid not in current_uids:
            if prev_elem.get('remove_policy'):
                removed.append(prev_elem)

    return removed


def find_gpo_removed_elements(
    current_gpos: Set[str],
    previous_elements: List[Dict]
) -> List[Dict]:
    '''
    Find elements from GPOs that have been unlinked.

    :param current_gpos: Set of currently linked GPO GUIDs
    :param previous_elements: Elements from previous gpupdate run
    :return: List of elements from unlinked GPOs
    '''
    removed = []
    for elem in previous_elements:
        elem_gpo = elem.get('policy_guid')
        if elem_gpo and elem_gpo not in current_gpos:
            if elem.get('remove_policy'):
                removed.append(elem)

    return removed


def is_element_applied(element: Dict, element_type: str, username: str = None) -> bool:
    '''
    Check if an element with applyOnce has already been applied.

    :param element: Element dictionary
    :param element_type: Type of element
    :param username: Username for user preferences, None for machine
    :return: True if element was already applied (should skip)
    '''
    if not element.get('apply_once'):
        return False

    previous = get_previous_elements(element_type, username)
    elem_uid = element.get('uid')

    logdata = {
        'element_type': element_type,
        'uid': elem_uid,
        'previous_count': len(previous)
    }
    log('D251', logdata)

    for prev_elem in previous:
        if prev_elem.get('uid') == elem_uid:
            applied = prev_elem.get('applied')
            logdata = {'uid': elem_uid, 'applied': applied}
            log('D252', logdata)
            if applied:
                return True

    return False


def mark_element_applied(
    element: Dict,
    element_type: str,
    username: str = None,
    element_obj=None
) -> None:
    '''
    Mark an element as applied in dconf storage.

    :param element: Element dictionary
    :param element_type: Type of element
    :param username: Username for user preferences, None for machine
    :param element_obj: Original element object to set applied attribute on
    '''
    elem_uid = element.get('uid')
    if not elem_uid:
        return

    timestamp = datetime.now().astimezone().strftime('%d.%m.%Y %H:%M:%S')
    element['applied'] = timestamp

    if element_obj is not None:
        element_obj.applied = timestamp


def get_current_gpo_guids() -> Set[str]:
    '''
    Get the set of currently linked GPO GUIDs from registry.

    :return: Set of GPO GUID strings
    '''
    guids = set()

    registry = Dconf_registry.get_storage()
    priority_prefix = Dconf_registry._GpoPriority

    for key in registry.keys():
        if key.startswith(priority_prefix + '/'):
            parts = key.split('/')
            if len(parts) >= 3:
                gpo_info = registry.get(key, {})
                if isinstance(gpo_info, dict):
                    name = gpo_info.get('name')
                    if name and name != 'Unknown' and name != 'Local Policy':
                        guids.add(name)

    return guids


class GppStateManager:
    '''
    Manages GPP element state across gpupdate runs.
    '''

    def __init__(self, username: str = None):
        self.username = username
        self.is_machine = (username is None or username == 'Machine')

        self.current_gpos = get_current_gpo_guids()

        self._previous_elements: Dict[str, List[Dict]] = {}
        self._removed_elements: Dict[str, List[Dict]] = {}

    def get_previous(self, element_type: str) -> List[Dict]:
        '''
        Get previous elements for a type, caching the result.

        :param element_type: Type of element
        :return: List of previous element dictionaries
        '''
        if element_type not in self._previous_elements:
            self._previous_elements[element_type] = get_previous_elements(
                element_type, self.username
            )
        return self._previous_elements[element_type]

    def find_removed(self, element_type: str, current: List[Dict]) -> List[Dict]:
        '''
        Find removed elements for a type.

        :param element_type: Type of element
        :param current: Current element list
        :return: List of removed elements
        '''
        previous = self.get_previous(element_type)
        removed = find_removed_elements(current, previous)

        removed.extend(
            find_gpo_removed_elements(self.current_gpos, previous)
        )

        self._removed_elements[element_type] = removed
        return removed

    def should_skip(self, element: Dict, element_type: str) -> bool:
        '''
        Check if element should be skipped (applyOnce already applied).

        :param element: Element dictionary
        :param element_type: Type of element
        :return: True if should skip application
        '''
        return is_element_applied(element, element_type, self.username)

    def mark_applied(self, element: Dict, element_type: str, element_obj=None) -> None:
        '''
        Mark element as applied.

        :param element: Element dictionary
        :param element_type: Type of element
        :param element_obj: Original element object to set applied attribute on
        '''
        mark_element_applied(element, element_type, self.username, element_obj=element_obj)


ELEMENT_TYPE_MAP = {
    'inifile': 'Inifiles',
    'fileentry': 'Files',
    'folderentry': 'Folders',
    'shortcut': 'Shortcuts',
    'drivemap': 'Drives',
    'envvar': 'Environmentvariables',
    'networkshare': 'Networkshares',
    'printer': 'Printers',
    'service': 'Services',
}


def get_element_type_name(element) -> str:
    '''
    Get the dconf storage type name for an element.

    :param element: GPP element object
    :return: Type name string
    '''
    class_name = element.__class__.__name__
    return ELEMENT_TYPE_MAP.get(class_name, class_name)
