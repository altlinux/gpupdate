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
from enum import Enum


from util.logging import slogm


class NTPServerType(Enum):
    NTP = 'NTP'


class ntp_applier:
    __module_name = 'NTPApplier'
    __module_experimental = True
    __module_enabled = False

    __ntp_branch = 'Software\\Policies\\Microsoft\\W32time\\Parameters'
    __ntp_client_branch = 'Software\\Policies\\Microsoft\\W32time\\TimeProviders\\NtpClient'
    __ntp_server_branch = 'Software\\Policies\\Microsoft\\W32time\\TimeProviders\\NtpServer'

    __ntp_key_address = 'NtpServer'
    __ntp_key_type = 'Type'
    __ntp_key_client_enabled = 'Enabled'
    __ntp_key_server_enabled = 'Enabled'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

        self.ntp_server_address_key = '{}\\{}'.format(self.__ntp_branch, self.__ntp_key_address)
        self.ntp_server_type = '{}\\{}'.format(self.__ntp_branch, self.__ntp_key_type)
        self.ntp_client_enabled = '{}\\{}'.format(self.__ntp_client_branch, self.__ntp_key_client_enabled)
        self.ntp_server_enabled = '{}\\{}'.format(self.__ntp_server_branch, self.__ntp_key_server_enabled)

    def run(self):
        server_type = self.storage.get_hklm_key(self.ntp_server_type)
        if NTPServerType.NTP.value != server_type:
            logging.warning(slogm('Unsupported NTP server type: {}'.format(server_type)))
        else:
            logging.debug(slogm('Configuring NTP server...'))

    def apply(self):
        if self.__module_enabled:
            logging.debug(slogm('Running NTP applier for machine'))
            self.run()
        else:
            logging.debug(slogm('NTP applier for machine will not be started'))

