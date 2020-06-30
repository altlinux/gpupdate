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

import logging
import os
import subprocess

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from .appliers.gsettings import (
    system_gsetting,
    user_gsetting
)
from util.logging import slogm

class gsettings_applier(applier_frontend):
    __module_name = 'GSettingsApplier'
    __module_experimental = True
    __module_enabled = False
    __registry_branch = 'Software\\BaseALT\\Policies\\gsettings'
    __global_schema = '/usr/share/glib-2.0/schemas'

    def __init__(self, storage):
        self.storage = storage
        gsettings_filter = '{}%'.format(self.__registry_branch)
        self.gsettings_keys = self.storage.filter_hklm_entries(gsettings_filter)
        self.gsettings = list()
        self.override_file = os.path.join(self.__global_schema, '0_policy.gschema.override')
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        # Cleanup settings from previous run
        if os.path.exists(self.override_file):
            logging.debug(slogm('Removing GSettings policy file from previous run'))
            os.remove(self.override_file)

        # Calculate all configured gsettings
        for setting in self.gsettings_keys:
            valuename = setting.hive_key.rpartition('\\')[2]
            rp = valuename.rpartition('.')
            schema = rp[0]
            path = rp[2]
            self.gsettings.append(system_gsetting(schema, path, setting.data))

        # Create GSettings policy with highest available priority
        for gsetting in self.gsettings:
            gsetting.apply()

        # Recompile GSettings schemas with overrides
        try:
            proc = subprocess.run(args=['/usr/bin/glib-compile-schemas', self.__global_schema], capture_output=True, check=True)
        except Exception as exc:
            logging.debug(slogm('Error recompiling global GSettings schemas'))

    def apply(self):
        if self.__module_enabled:
            logging.debug(slogm('Running GSettings applier for machine'))
        else:
            logging.debug(slogm('GSettings applier for machine will not be started'))


class gsettings_applier_user(applier_frontend):
    __module_name = 'GSettingsApplierUser'
    __module_experimental = True
    __module_enabled = False
    __registry_branch = 'Software\\BaseALT\\Policies\\gsettings'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        gsettings_filter = '{}%'.format(self.__registry_branch)
        self.gsettings_keys = self.storage.filter_hkcu_entries(self.sid, gsettings_filter)
        self.gsettings = list()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_enabled)

    def run(self):
        for setting in self.gsettings_keys:
            valuename = setting.hive_key.rpartition('\\')[2]
            rp = valuename.rpartition('.')
            schema = rp[0]
            path = rp[2]
            self.gsettings.append(user_gsetting(schema, path, setting.data))

        for gsetting in self.gsettings:
            gsetting.apply()

    def user_context_apply(self):
        if self.__module_enabled:
            logging.debug(slogm('Running GSettings applier for user in user context'))
            self.run()
        else:
            logging.debug(slogm('GSettings applier for user in user context will not be started'))

    def admin_context_apply(self):
        '''
        Not implemented because there is no point of doing so.
        '''
        pass

