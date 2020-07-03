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
import subprocess

from util.logging import slogm
from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from .appliers.firewall_rule import FirewallRule

class firewall_applier(applier_frontend):
    __module_name = 'FirewallApplier'
    __module_experimental = True
    __module_enabled = False
    __firewall_branch = 'SOFTWARE\\Policies\\Microsoft\\WindowsFirewall\\FirewallRules'
    __firewall_switch = 'SOFTWARE\\Policies\\Microsoft\\WindowsFirewall\\DomainProfile\\EnableFirewall'
    __firewall_reset_cmd = ['/usr/bin/alterator-net-iptables', 'reset']

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
        if self.__module_enabled:
            logging.debug(slogm('Running Firewall applier for machine'))
            if '0' == self.firewall_enabled:
                logging.debug(slogm('Firewall is disabled, settings will be reset'))
                proc = subprocess.Popen(self.__firewall_reset_cmd)
                proc.wait()
            else:
                logging.debug(slogm('Firewall is enabled'))
                self.run()
        else:
            logging.debug(slogm('Firewall applier will not be started'))

