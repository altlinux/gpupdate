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

from .applier_frontend import (
      applier_frontend
    , check_enabled
    , check_windows_mapping_enabled
)
from .appliers.polkit import polkit
from util.logging import log

class polkit_applier(applier_frontend):
    __module_name = 'PolkitApplier'
    __module_experimental = False
    __module_enabled = True
    __deny_all_win = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices\\Deny_All'
    __registry_branch = 'Software\\BaseALT\\Policies\\Polkit\\'
    __polkit_map = {
        __deny_all_win: ['49-gpoa_disk_permissions', { 'Deny_All': 0 }],
        __registry_branch : ['49-group_policy_permissions', {}]
    }

    def __init__(self, storage):
        self.storage = storage
        deny_all_win = None
        if check_windows_mapping_enabled(self.storage):
            deny_all_win = storage.filter_hklm_entries(self.__deny_all_win).first()
        # Deny_All hook: initialize defaults
        polkit_filter = '{}%'.format(self.__registry_branch)
        self.polkit_keys = self.storage.filter_hklm_entries(polkit_filter)
        template_file = self.__polkit_map[self.__deny_all_win][0]
        template_vars = self.__polkit_map[self.__deny_all_win][1]
        template_file_all = self.__polkit_map[self.__registry_branch][0]
        template_vars_all = self.__polkit_map[self.__registry_branch][1]
        res_no =  list()
        res_yes = list()
        res_auth_self = list()
        res_auth_admin = list()
        res_auth_self_keep = list()
        res_auth_admin_keep = list()
        for it_data in self.polkit_keys:
            if it_data.data == 'No':
                res_no.append(it_data.valuename)
            elif it_data.data == 'Yes':
                res_yes.append(it_data.valuename)
            elif it_data.data == 'Auth_self':
                res_auth_self.append(it_data.valuename)
            elif it_data.data == 'Auth_admin':
                res_auth_admin.append(it_data.valuename)
            elif it_data.data == 'Auth_self_keep':
                res_auth_self_keep.append(it_data.valuename)
            elif it_data.data == 'Auth_admin_keep':
                res_auth_admin_keep.append(it_data.valuename)
        self.__polkit_map[self.__registry_branch][1]['res_no'] = res_no
        self.__polkit_map[self.__registry_branch][1]['res_yes'] = res_yes
        self.__polkit_map[self.__registry_branch][1]['res_auth_self'] = res_auth_self
        self.__polkit_map[self.__registry_branch][1]['res_auth_self_keep'] = res_auth_self_keep
        self.__polkit_map[self.__registry_branch][1]['res_auth_admin'] = res_auth_admin
        self.__polkit_map[self.__registry_branch][1]['res_auth_admin_keep'] = res_auth_admin_keep
        if deny_all_win:
            logdata = dict()
            logdata['Deny_All_win'] = deny_all_win.data
            log('D69', logdata)
            self.__polkit_map[self.__deny_all_win][1]['Deny_All'] = deny_all_win.data
        else:
            log('D71')
        self.policies = []
        self.policies.append(polkit(template_file, template_vars))
        self.policies.append(polkit(template_file_all, template_vars_all))
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        if self.__module_enabled:
            log('D73')
            for policy in self.policies:
                policy.generate()
        else:
            log('D75')

class polkit_applier_user(applier_frontend):
    __module_name = 'PolkitApplierUser'
    __module_experimental = False
    __module_enabled = True
    __deny_all_win = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices\\Deny_All'
    __registry_branch = 'Software\\BaseALT\\Policies\\Polkit\\'
    __polkit_map = {
            __deny_all_win: ['48-gpoa_disk_permissions_user', { 'Deny_All': 0, 'User': '' }],
            __registry_branch : ['48-group_policy_permissions_user', {'User': ''}]
    }

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        deny_all_win = None
        if check_windows_mapping_enabled(self.storage):
            deny_all_win = storage.filter_hkcu_entries(self.sid, self.__deny_all_win).first()
        polkit_filter = '{}%'.format(self.__registry_branch)
        self.polkit_keys = self.storage.filter_hklm_entries(self.sid, polkit_filter)
        # Deny_All hook: initialize defaults
        template_file = self.__polkit_map[self.__deny_all_win][0]
        template_vars = self.__polkit_map[self.__deny_all_win][1]
        template_file_all = self.__polkit_map[self.__registry_branch][0]
        template_vars_all = self.__polkit_map[self.__registry_branch][1]
        res_no =  list()
        res_yes = list()
        res_auth_self = list()
        res_auth_admin = list()
        res_auth_self_keep = list()
        res_auth_admin_keep = list()
        for it_data in self.polkit_keys:
            if it_data.data == 'No':
                res_no.append(it_data.valuename)
            elif it_data.data == 'Yes':
                res_yes.append(it_data.valuename)
            elif it_data.data == 'Auth_self':
                res_auth_self.append(it_data.valuename)
            elif it_data.data == 'Auth_admin':
                res_auth_admin.append(it_data.valuename)
            elif it_data.data == 'Auth_self_keep':
                res_auth_self_keep.append(it_data.valuename)
            elif it_data.data == 'Auth_admin_keep':
                res_auth_admin_keep.append(it_data.valuename)
        self.__polkit_map[self.__registry_branch][1]['User'] = self.username
        self.__polkit_map[self.__registry_branch][1]['res_no'] = res_no
        self.__polkit_map[self.__registry_branch][1]['res_yes'] = res_yes
        self.__polkit_map[self.__registry_branch][1]['res_auth_self'] = res_auth_self
        self.__polkit_map[self.__registry_branch][1]['res_auth_self_keep'] = res_auth_self_keep
        self.__polkit_map[self.__registry_branch][1]['res_auth_admin'] = res_auth_admin
        self.__polkit_map[self.__registry_branch][1]['res_auth_admin_keep'] = res_auth_admin_keep
        if deny_all_win:
            logdata = dict()
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

    def user_context_apply(self):
        pass

    def admin_context_apply(self):
        '''
        Trigger control facility invocation.
        '''
        if self.__module_enabled:
            log('D74')
            for policy in self.policies:
                policy.generate()
        else:
            log('D76')


