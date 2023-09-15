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



import subprocess
from enum import Enum


from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import log


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

    def __init__(self, storage):
        self.storage = storage

        self.ntp_server_address_key = '{}\\{}'.format(self.__ntp_branch, self.__ntp_key_address)
        self.ntp_server_type = '{}\\{}'.format(self.__ntp_branch, self.__ntp_key_type)
        self.ntp_client_enabled = '{}\\{}'.format(self.__ntp_client_branch, self.__ntp_key_client_enabled)
        self.ntp_server_enabled = '{}\\{}'.format(self.__ntp_server_branch, self.__ntp_key_server_enabled)

        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def _chrony_as_client(self):
        command = ['/usr/sbin/control', 'chrony', 'client']
        proc = subprocess.Popen(command)
        proc.wait()

    def _chrony_as_server(self):
        command = ['/usr/sbin/control', 'chrony', 'server']
        proc = subprocess.Popen(command)
        proc.wait()

    def _start_chrony_client(self, server=None):
        srv = None
        if server:
            srv = server.data.rpartition(',')[0]
            logdata = dict()
            logdata['srv'] = srv
            log('D122', logdata)

        start_command = ['/usr/bin/systemctl', 'start', 'chronyd']
        chrony_set_server = ['/usr/bin/chronyc', 'add', 'server', srv]
        chrony_disconnect_all = ['/usr/bin/chronyc', 'offline']
        chrony_connect = ['/usr/bin/chronyc', 'online', srv]

        log('D123')

        proc = subprocess.Popen(start_command)
        proc.wait()

        if srv:
            logdata = dict()
            logdata['srv'] = srv
            log('D124', logdata)

            proc = subprocess.Popen(chrony_disconnect_all)
            proc.wait()

            proc = subprocess.Popen(chrony_set_server)
            proc.wait()

            proc = subprocess.Popen(chrony_connect)
            proc.wait()

    def _stop_chrony_client(self):
        stop_command = ['/usr/bin/systemctl', 'stop', 'chronyd']
        log('D125')
        proc = subprocess.Popen(stop_command)
        proc.wait()

    def run(self):
        server_type = self.storage.get_hklm_entry(self.ntp_server_type)
        server_address = self.storage.get_hklm_entry(self.ntp_server_address_key)
        ntp_server_enabled = self.storage.get_hklm_entry(self.ntp_server_enabled)
        ntp_client_enabled = self.storage.get_hklm_entry(self.ntp_client_enabled)

        if server_type and server_type.data:
            if NTPServerType.NTP.value != server_type.data:
                logdata = dict()
                logdata['server_type'] = server_type
                log('W10', logdata)
            else:
                log('D126')
                if ntp_server_enabled:
                    if '1' == ntp_server_enabled.data and server_address:
                        log('D127')
                        self._start_chrony_client(server_address)
                        self._chrony_as_server()
                    elif '0' == ntp_server_enabled.data:
                        log('D128')
                        self._chrony_as_client()
                    else:
                        log('D129')

                elif ntp_client_enabled:
                    if '1' == ntp_client_enabled.data:
                        log('D130')
                        self._start_chrony_client()
                    elif '0' == ntp_client_enabled.data:
                        log('D131')
                        self._stop_chrony_client()
                    else:
                        log('D132')

    def apply(self):
        if self.__module_enabled:
            log('D121')
            self.run()
        else:
            log('D133')

