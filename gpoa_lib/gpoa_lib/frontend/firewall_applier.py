#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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


import os
import subprocess

from ..util.logging import log

from .applier_frontend import applier_frontend, check_enabled
from .appliers.firewall_rule import FirewallRule
from ..applier_result import ApplierResult, ItemStatus, STATUS_PARTIAL, RESULT_SUCCESS, RESULT_FAILED


class firewall_applier(applier_frontend):
    __module_name = 'FirewallApplier'
    __module_experimental = True
    __module_enabled = False
    __firewall_branch = 'SOFTWARE\\Policies\\Microsoft\\WindowsFirewall\\FirewallRules'
    __firewall_switch = 'SOFTWARE\\Policies\\Microsoft\\WindowsFirewall\\DomainProfile\\EnableFirewall'
    __firewall_reset_cmd = ['/usr/bin/alterator-net-iptables', 'reset']
    __firewall_reset_cmd_path = '/usr/bin/alterator-net-iptables'

    def __init__(self, storage):
        self.storage = storage
        self.firewall_settings = self.storage.filter_hklm_entries('{}%'.format(self.__firewall_branch))
        self.firewall_enabled = self.storage.get_hklm_entry(self.__firewall_switch)
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        for setting in self.firewall_settings:
            rule = FirewallRule(setting.data)
            rule.apply()

    def apply(self):
        if not os.path.exists(self.__firewall_reset_cmd_path):
            log('D120', {'not_found_cmd': self.__firewall_reset_cmd_path})
            return ApplierResult.skipped('firewall', 'reset command not found')
        if self.__module_enabled:
            log('I29')
            log('D117')
            items = []
            try:
                if '1' == self.firewall_enabled:
                    log('D118')
                    self.run()
                    items.append(ItemStatus(key='rules', action='set', result=RESULT_SUCCESS))
                else:
                    log('D119')
                    with subprocess.Popen(self.__firewall_reset_cmd) as proc:
                        proc.wait(timeout=30)
                    items.append(ItemStatus(key='reset', action='set', result=RESULT_SUCCESS))
                failed = sum(1 for i in items if i.result == RESULT_FAILED)
                status = STATUS_PARTIAL if failed else STATUS_APPLIED
                return ApplierResult(name='firewall', status=status, items=items)
            except Exception as exc:
                return ApplierResult.failed('firewall', str(exc))
        else:
            log('D120')
            return ApplierResult.skipped('firewall')

