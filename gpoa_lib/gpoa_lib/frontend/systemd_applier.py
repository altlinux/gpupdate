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

from .applier_frontend import applier_frontend, DualContextApplier, check_enabled
from .appliers.systemd import systemd_unit
from ..applier_result import ApplierResult, ItemStatus, STATUS_APPLIED, STATUS_SKIPPED, STATUS_PARTIAL, RESULT_SUCCESS, RESULT_FAILED


class systemd_applier(applier_frontend):
    __module_name = 'SystemdApplier'
    __module_experimental = False
    __module_enabled = True
    __registry_branch = 'Software/BaseALT/Policies/SystemdUnits'

    def __init__(self, storage):
        self.storage = storage
        self.systemd_unit_settings = self.storage.filter_hklm_entries(self.__registry_branch)
        self.units = []
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        items = []
        for setting in self.systemd_unit_settings:
            try:
                self.units.append(systemd_unit(setting.valuename, int(setting.data)))
                logdata = {'unit': format(setting.valuename)}
                log('I4', logdata)
            except Exception as exc:
                logdata = {'unit': format(setting.valuename), 'exc': exc}
                log('I5', logdata)
                items.append(ItemStatus(key=setting.valuename, action='set', result=RESULT_FAILED, detail=str(exc)))
        for unit in self.units:
            try:
                unit.apply()
                items.append(ItemStatus(key=unit.unit_name, action='set', result=RESULT_SUCCESS))
            except Exception as exc:
                logdata = {'unit': unit.unit_name, 'exc': exc}
                log('E45', logdata)
                items.append(ItemStatus(key=unit.unit_name, action='set', result=RESULT_FAILED, detail=str(exc)))
        return items

    def apply(self):
        if self.__module_enabled:
            log('I19')
            log('D78')
            items = self.run()
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='systemd', status=status, items=items)
        else:
            log('D79')
            return ApplierResult.skipped('systemd')

class systemd_applier_user(DualContextApplier):
    __module_name = 'SystemdApplierUser'
    __module_experimental = False
    __module_enabled = True
    __registry_branch = 'Software/BaseALT/Policies/SystemdUnits'

    def __init__(self, storage, username):
        self.storage = storage

    def user_context_apply(self):
        pass

    def admin_context_apply(self):
        pass

