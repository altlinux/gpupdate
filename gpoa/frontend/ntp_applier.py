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
from enum import Enum


from applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import slogm


class NTPServerType(Enum):
    NTP = 'NTP'


class ntp_applier(applier_frontend):
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

    __chrony_config = '/etc/chrony.conf'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

        self.ntp_server_address_key = '{}\\{}'.format(self.__ntp_branch, self.__ntp_key_address)
        self.ntp_server_type = '{}\\{}'.format(self.__ntp_branch, self.__ntp_key_type)
        self.ntp_client_enabled = '{}\\{}'.format(self.__ntp_client_branch, self.__ntp_key_client_enabled)
        self.ntp_server_enabled = '{}\\{}'.format(self.__ntp_server_branch, self.__ntp_key_server_enabled)

        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def _start_ntpd_server(self, server=None):
        start_command = ['systemctl', 'start', 'ntpd']

        logging.debug(slogm('Starting ntpd as a server'))

        proc = subprocess.Popen(start_command)
        proc.wait()

    def _stop_ntpd_server(self):
        stop_command = ['systemctl', 'stop', 'ntpd']

        logging.debug(slogm('Stopping ntpd server'))

        proc = subprocess.Popen(stop_command)
        proc.wait()

    def _start_ntpd_client(self, server=None):
        start_command = ['systemctl', 'start', 'ntpd']

        logging.debug(slogm('Starting ntpd as a client'))

        proc = subprocess.Popen(start_command)
        proc.wait()

    def _stop_ntpd_client(self):
        stop_command = ['systemctl', 'stop', 'ntpd']

        logging.debug(slogm('Stopping ntpd client'))

        proc = subprocess.Popen(stop_command)
        proc.wait()

    def _start_chrony_client(self, server=None):
        start_command = ['systemctl', 'start', 'chronyd']
        chrony_set_server = ['chronyc', 'add', 'server', server]
        chrony_disconnect_all = ['chronyc', 'offline']
        chrony_connect = ['chronyc', 'online', server]

        logging.debug(slogm('Starting Chrony daemon'))

        proc = subprocess.Popen(start_command)
        proc.wait()

        if server:
            logging.debug(slogm('Setting reference NTP server to {}'.format(server)))

            proc = subprocess.Popen(chrony_disconnect_all)
            proc.wait()

            proc = subprocess.Popen(chrony_set_server)
            proc.wait()

            proc = subprocess.Popen(chrony_connect)
            proc.wait()

    def _stop_chrony_client(self):
        stop_command = ['systemctl', 'stop', 'chronyd']

        logging.debug(slogm('Stopping Chrony daemon'))

        proc = subprocess.Popen(stop_command)
        proc.wait()

    def run(self):
        server_type = self.storage.get_hklm_key(self.ntp_server_type)
        server_address = self.storage.get_hklm_key(self.ntp_server_address_key)
        ntp_server_enabled = self.storage.get_hklm_key(self.ntp_server_enabled)
        ntp_client_enabled = self.storage.get_hklm_key(self.ntp_client_enabled)

        if NTPServerType.NTP.value != server_type:
            logging.warning(slogm('Unsupported NTP server type: {}'.format(server_type)))
        else:
            logging.debug(slogm('Configuring NTP server...'))
            if '1' == ntp_server_enabled:
                self._stop_chrony_client()
                self._start_ntpd_server(server_address)
                if '1' == ntp_client_enabled:
                    self._stop_chrony_client()
                    self._start_ntpd_client(server_address)
            elif '0' == ntp_server_enabled:
                self._stop_ntpd_server()
                if '1' == ntp_client_enabled:
                    self._stop_ntpd_client()
                    self._start_chrony_client(server_address)
                elif '0' == ntp_client_enabled:
                    self._stop_ntpd_client()
                    self._stop_chrony_client()

    def apply(self):
        if self.__module_enabled:
            logging.debug(slogm('Running NTP applier for machine'))
            self.run()
        else:
            logging.debug(slogm('NTP applier for machine will not be started'))

