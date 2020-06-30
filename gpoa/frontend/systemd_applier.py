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
)
from .appliers.systemd import systemd_unit
from util.logging import slogm

import logging

class systemd_applier(applier_frontend):
    __module_name = 'SystemdApplier'
    __module_experimental = False
    __module_enabled = True
    __registry_branch = 'Software\\BaseALT\\Policies\\SystemdUnits'

    def __init__(self, storage):
        self.storage = storage
        self.systemd_unit_settings = self.storage.filter_hklm_entries('Software\\BaseALT\\Policies\\SystemdUnits%')
        self.units = []
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        for setting in self.systemd_unit_settings:
            valuename = setting.hive_key.rpartition('\\')[2]
            try:
                self.units.append(systemd_unit(valuename, int(setting.data)))
                logging.info(slogm('Working with systemd unit {}'.format(valuename)))
            except Exception as exc:
                logging.info(slogm('Unable to work with systemd unit {}: {}'.format(valuename, exc)))
        for unit in self.units:
            try:
                unit.apply()
            except:
                logging.error(slogm('Failed applying unit {}'.format(unit.unit_name)))

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        if self.__module_enabled:
            logging.debug(slogm('Running systemd applier for machine'))
            self.run()
        else:
            logging.debug(slogm('systemd applier for machine will not be started'))

class systemd_applier_user(applier_frontend):
    __module_name = 'SystemdApplierUser'
    __module_experimental = False
    __module_enabled = True
    __registry_branch = 'Software\\BaseALT\\Policies\\SystemdUnits'

    def __init__(self, storage, sid, username):
        self.storage = storage

    def user_context_apply(self):
        pass

    def admin_context_apply(self):
        pass

