#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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

from .applier_frontend import applier_frontend, check_enabled
from .appliers.control import control
from ..applier_result import ApplierResult, ItemStatus, STATUS_APPLIED, STATUS_PARTIAL, RESULT_SUCCESS, RESULT_FAILED


class control_applier(applier_frontend):
    __module_name = 'ControlApplier'
    __module_experimental = False
    __module_enabled = True
    _registry_branch = 'Software/BaseALT/Policies/Control'

    def __init__(self, storage):
        self.storage = storage
        self.control_settings = self.storage.filter_hklm_entries(self._registry_branch)
        self.controls = []
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        items = []
        for setting in self.control_settings:
            valuename = setting.hive_key.rpartition('/')[2]
            try:
                self.controls.append(control(valuename, int(setting.data)))
                logdata = {'control': valuename, 'value': setting.data}
                log('I3', logdata)
            except ValueError as exc:
                try:
                    ctl = control(valuename, setting.data)
                except Exception as exc:
                    logdata = {'Exception': exc}
                    log('I3', logdata)
                    items.append(ItemStatus(key=valuename, action='set', result=RESULT_FAILED, detail=str(exc)))
                    continue
                self.controls.append(ctl)
                logdata = {'control': valuename, 'with string value': setting.data}
                log('I3', logdata)
            except Exception as exc:
                logdata = {'control': valuename, 'exc': exc}
                log('E39', logdata)
                items.append(ItemStatus(key=valuename, action='set', result=RESULT_FAILED, detail=str(exc)))
        for cont in self.controls:
            success = cont.set_control_status()
            name = cont.get_control_name()
            if success:
                items.append(ItemStatus(key=name, action='set', result=RESULT_SUCCESS))
            else:
                items.append(ItemStatus(key=name, action='set', result=RESULT_FAILED))
        return items

    def apply(self):
        if self.__module_enabled:
            log('I17')
            log('D67')
            items = self.run()
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='control', status=status, items=items)
        else:
            log('E40')
            return ApplierResult.skipped('control')
