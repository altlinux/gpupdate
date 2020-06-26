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
    , check_module_enabled
)
from .appliers.control import control
from util.logging import slogm

import logging

class control_applier(applier_frontend):
    __module_name = 'control_applier'
    __module_experimental = False
    __module_enabled = True
    _registry_branch = 'Software\\BaseALT\\Policies\\Control'

    def __init__(self, storage):
        self.storage = storage
        self.control_settings = self.storage.filter_hklm_entries('Software\\BaseALT\\Policies\\Control%')
        self.controls = list()
        self.__module_enabled = check_module_enabled(self.storage, self.__module_name, self.__module_enabled)

    def run(self):
        for setting in self.control_settings:
            valuename = setting.hive_key.rpartition('\\')[2]
            try:
                self.controls.append(control(valuename, int(setting.data)))
                logging.info(slogm('Working with control {}'.format(valuename)))
            except ValueError as exc:
                self.controls.append(control(valuename, setting.data))
                logging.info(slogm('Working with control {} with string value'.format(valuename)))
            except Exception as exc:
                logging.info(slogm('Unable to work with control {}: {}'.format(valuename, exc)))
        #for e in polfile.pol_file.entries:
        #    print('{}:{}:{}:{}:{}'.format(e.type, e.data, e.valuename, e.keyname))
        for cont in self.controls:
            cont.set_control_status()

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        if self.__module_enabled:
            self.run()

