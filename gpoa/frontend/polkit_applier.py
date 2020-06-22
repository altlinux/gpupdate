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

from .applier_frontend import applier_frontend
from .appliers.polkit import polkit
from util.logging import slogm

import logging

class polkit_applier(applier_frontend):
    __deny_all = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices\\Deny_All'
    __polkit_map = {
        __deny_all: ['49-gpoa_disk_permissions', { 'Deny_All': 0 }]
    }

    def __init__(self, storage):
        self.storage = storage
        deny_all = storage.filter_hklm_entries(self.__deny_all).first()
        # Deny_All hook: initialize defaults
        template_file = self.__polkit_map[self.__deny_all][0]
        template_vars = self.__polkit_map[self.__deny_all][1]
        if deny_all:
            logging.debug(slogm('Deny_All setting found: {}'.format(deny_all.data)))
            self.__polkit_map[self.__deny_all][1]['Deny_All'] = deny_all.data
        else:
            logging.debug(slogm('Deny_All setting not found'))
        self.policies = []
        self.policies.append(polkit(template_file, template_vars))

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for policy in self.policies:
            policy.generate()

class polkit_applier_user(applier_frontend):
    __deny_all = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices\\Deny_All'
    __polkit_map = {
            __deny_all: ['48-gpoa_disk_permissions_user', { 'Deny_All': 0, 'User': '' }]
    }

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

        deny_all = storage.filter_hkcu_entries(self.sid, self.__deny_all).first()
        # Deny_All hook: initialize defaults
        template_file = self.__polkit_map[self.__deny_all][0]
        template_vars = self.__polkit_map[self.__deny_all][1]
        if deny_all:
            logging.debug(slogm('Deny_All setting for user {} found: {}'.format(self.username, deny_all.data)))
            self.__polkit_map[self.__deny_all][1]['Deny_All'] = deny_all.data
            self.__polkit_map[self.__deny_all][1]['User'] = self.username
        else:
            logging.debug(slogm('Deny_All setting not found'))
        self.policies = []
        self.policies.append(polkit(template_file, template_vars, self.username))

    def user_context_apply(self):
        pass

    def admin_context_apply(self):
        '''
        Trigger control facility invocation.
        '''
        for policy in self.policies:
            policy.generate()

