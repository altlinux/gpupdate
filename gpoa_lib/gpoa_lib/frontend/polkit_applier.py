#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
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

from ..util.logging import log
from ..storage.dconf_registry import Dconf_registry

from .applier_frontend import (
    applier_frontend,
    DualContextApplier,
    check_enabled,
    check_windows_mapping_enabled
)
from .appliers.polkit import polkit
from ..applier_result import ApplierResult, ItemStatus, STATUS_APPLIED, STATUS_PARTIAL, RESULT_SUCCESS, RESULT_FAILED


class polkit_applier(applier_frontend):
    __module_name = 'PolkitApplier'
    __module_experimental = False
    __module_enabled = True
    __deny_all_win = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices\\Deny_All'
    __registry_branch = 'Software\\BaseALT\\Policies\\Polkit\\'
    __registry_locks_branch = 'Software\\BaseALT\\Policies\\PolkitLocks\\'
    __polkit_map = {
        __deny_all_win: ['49-gpoa_disk_permissions', { 'Deny_All': 0 }],
        __registry_branch : ['49-alt_group_policy_permissions', {}],
        __registry_locks_branch : ['47-alt_group_policy_permissions', {}]
    }

    def __init__(self, storage):
        self.storage = storage
        deny_all_win = None
        if check_windows_mapping_enabled(self.storage):
            deny_all_win = storage.filter_hklm_entries(self.__deny_all_win).first()
        # Deny_All hook: initialize defaults
        polkit_filter = '{}%'.format(self.__registry_branch)
        polkit_locks_filter = '{}%'.format(self.__registry_locks_branch)
        self.polkit_keys = self.storage.filter_hklm_entries(polkit_filter)
        self.polkit_locks = self.storage.filter_hklm_entries(polkit_locks_filter)
        template_file = self.__polkit_map[self.__deny_all_win][0]
        template_vars = self.__polkit_map[self.__deny_all_win][1]
        template_file_all = self.__polkit_map[self.__registry_branch][0]
        template_vars_all = self.__polkit_map[self.__registry_branch][1]
        template_file_all_lock = self.__polkit_map[self.__registry_locks_branch][0]
        template_vars_all_lock = self.__polkit_map[self.__registry_locks_branch][1]
        locks = []
        for lock in self.polkit_locks:
            if bool(int(lock.data)):
                locks.append(lock.valuename)

        # Deduplicate conflicting verdicts for the same action:
        # storage merge order reflects GPO precedence, the entry
        # merged last wins and becomes the only verdict rendered.
        action_verdicts = {}
        for it_data in self.polkit_keys:
            action_verdicts[it_data.valuename] = it_data.data

        dict_lists_rules = {'No': [[], []],
                            'Yes': [[], []],
                            'Auth_self' : [[], []],
                            'Auth_admin': [[], []],
                            'Auth_self_keep': [[], []],
                            'Auth_admin_keep': [[], []]}

        for action in sorted(action_verdicts):
            verdict = action_verdicts[action]
            if verdict not in dict_lists_rules:
                continue
            if action in locks:
                dict_lists_rules[verdict][1].append(action)
            else:
                dict_lists_rules[verdict][0].append(action)

        for key, item in dict_lists_rules.items():
            self.__polkit_map[self.__registry_branch][1][key] = item[0]
            self.__polkit_map[self.__registry_locks_branch][1][key] = item[1]

        if deny_all_win:
            logdata = {}
            logdata['Deny_All_win'] = deny_all_win.data
            log('D69', logdata)
            self.__polkit_map[self.__deny_all_win][1]['Deny_All'] = deny_all_win.data
        else:
            log('D71')
        self.policies = []
        self.policies.append(polkit(template_file, template_vars))
        self.policies.append(polkit(template_file_all, template_vars_all))
        self.policies.append(polkit(template_file_all_lock, template_vars_all_lock))
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def apply(self):
        if self.__module_enabled:
            log('I18')
            log('D73')
            items = []
            for policy in self.policies:
                try:
                    policy.generate()
                    items.append(ItemStatus(key=policy.template_name, action='create', result=RESULT_SUCCESS))
                except Exception as exc:
                    items.append(ItemStatus(key=policy.template_name, action='create', result=RESULT_FAILED, detail=str(exc)))
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='polkit', status=status, items=items)
        else:
            log('D75')
            return ApplierResult.skipped('polkit')

class polkit_applier_user(DualContextApplier):
    __module_name = 'PolkitApplierUser'
    __module_experimental = False
    __module_enabled = True
    __deny_all_win = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices\\Deny_All'
    __registry_branch = 'Software\\BaseALT\\Policies\\Polkit\\'
    __polkit_map = {
            __deny_all_win: ['48-gpoa_disk_permissions_user', { 'Deny_All': 0, 'User': '' }],
            __registry_branch : ['48-alt_group_policy_permissions_user', {'User': ''}]
    }

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        deny_all_win = None
        if check_windows_mapping_enabled(self.storage):
            deny_all_win = storage.filter_hkcu_entries(self.__deny_all_win).first()
        polkit_filter = '{}%'.format(self.__registry_branch)
        self.polkit_keys = self.storage.filter_hkcu_entries(polkit_filter)
        # Machine policy takes precedence: actions already defined by
        # machine-scoped policy must not be overridden per user, so
        # they are excluded from the user-scoped rules file.
        machine_polkit_actions = self._get_machine_polkit_actions()
        # Deny_All hook: initialize defaults
        template_file = self.__polkit_map[self.__deny_all_win][0]
        template_vars = self.__polkit_map[self.__deny_all_win][1]
        template_file_all = self.__polkit_map[self.__registry_branch][0]
        template_vars_all = self.__polkit_map[self.__registry_branch][1]

        # Deduplicate conflicting verdicts for the same action: the
        # entry merged last wins (GPO precedence), only that verdict
        # is rendered. Actions defined by machine policy are skipped.
        action_verdicts = {}
        for it_data in self.polkit_keys:
            if it_data.valuename in machine_polkit_actions:
                continue
            action_verdicts[it_data.valuename] = it_data.data

        dict_lists_rules = {'No': [],
                            'Yes': [],
                            'Auth_self': [],
                            'Auth_admin': [],
                            'Auth_self_keep': [],
                            'Auth_admin_keep': []}

        for action in sorted(action_verdicts):
            verdict = action_verdicts[action]
            if verdict in dict_lists_rules:
                dict_lists_rules[verdict].append(action)

        self.__polkit_map[self.__registry_branch][1]['User'] = self.username

        for key, item in dict_lists_rules.items():
            self.__polkit_map[self.__registry_branch][1][key] = item

        if deny_all_win and not self._machine_defines_deny_all():
            logdata = {}
            logdata['user'] = self.username
            logdata['Deny_All_win'] = deny_all_win.data
            log('D70', logdata)
            self.__polkit_map[self.__deny_all_win][1]['Deny_All'] = deny_all_win.data
            self.__polkit_map[self.__deny_all_win][1]['User'] = self.username
        else:
            log('D72')
        self.policies = []
        self.policies.append(polkit(template_file, template_vars, self.username))
        self.policies.append(polkit(template_file_all, template_vars_all, self.username))
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def _get_machine_polkit_actions(self):
        '''
        Read actions defined by machine-scoped polkit policy from the
        machine dconf database. Returns an empty set when the machine
        database is unavailable.
        '''
        actions = set()
        try:
            machine_dict = Dconf_registry.get_dictionary_from_dconf_file_db()
            entries = Dconf_registry.filter_entries(
                self.__registry_branch.replace('\\', '/') + '/', machine_dict)
            for key in entries:
                parts = [p for p in key.split('/') if p]
                if parts:
                    actions.add(parts[-1])
        except Exception as exc:
            logdata = {'exc': str(exc)}
            log('D334', logdata)
        return actions

    def _machine_defines_deny_all(self):
        '''
        Check whether machine-scoped policy defines the Deny_All flag.
        '''
        try:
            machine_dict = Dconf_registry.get_dictionary_from_dconf_file_db()
            entries = Dconf_registry.filter_entries(
                self.__deny_all_win.replace('\\', '/') + '/', machine_dict)
            return bool(entries)
        except Exception as exc:
            logdata = {'exc': str(exc)}
            log('D334', logdata)
            return False

    def user_context_apply(self):
        pass

    def admin_context_apply(self):
        if self.__module_enabled:
            log('D74')
            items = []
            for policy in self.policies:
                try:
                    policy.generate()
                    items.append(ItemStatus(key=policy.template_name, action='create', result=RESULT_SUCCESS))
                except Exception as exc:
                    items.append(ItemStatus(key=policy.template_name, action='create', result=RESULT_FAILED, detail=str(exc)))
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='polkit_user', status=status, items=items)
        else:
            log('D76')
            return ApplierResult.skipped('polkit_user')


