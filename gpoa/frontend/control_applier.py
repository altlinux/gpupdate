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
from .appliers.control import control
from util.logging import slogm, log

import logging

class control_applier(applier_frontend):
    __module_name = 'ControlApplier'
    __module_experimental = False
    __module_enabled = True
    _registry_branch = 'Software/BaseALT/Policies/Control'

    def __init__(self, storage):
        self.storage = storage
        self.control_settings = self.storage.filter_hklm_entries(self._registry_branch)
        self.controls = list()
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        for setting in self.control_settings:
            valuename = setting.hive_key.rpartition('/')[2]
            try:
                self.controls.append(control(valuename, int(setting.data)))
                logdata = dict()
                logdata['control'] = valuename
                logdata['value'] = setting.data
                log('I3', logdata)
            except ValueError as exc:
                try:
                    ctl = control(valuename, setting.data)
                except Exception as exc:
                    logdata = {'Exception': exc}
                    log('I3', logdata)
                    continue
                self.controls.append(ctl)
                logdata = dict()
                logdata['control'] = valuename
                logdata['with string value'] = setting.data
                log('I3', logdata)
            except Exception as exc:
                logdata = dict()
                logdata['control'] = valuename
                logdata['exc'] = exc
                log('E39', logdata)
        #for e in polfile.pol_file.entries:
        #    print('{}:{}:{}:{}:{}'.format(e.type, e.data, e.valuename, e.keyname))
        for cont in self.controls:
            cont.set_control_status()

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        if self.__module_enabled:
            log('D67')
            self.run()
        else:
            log('E40')
