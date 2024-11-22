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

from enum import Enum
import subprocess

def getprops(param_list):
    props = dict()

    for entry in param_list:
        lentry = entry.lower()
        if lentry.startswith('action'):
            props['action'] = lentry.rpartition('=')[2]
        if lentry.startswith('protocol'):
            props['protocol'] = lentry.rpartition('=')[2]
        if lentry.startswith('dir'):
            props['dir'] = lentry.rpartition('=')[2]

    return props


def get_ports(param_list):
    portlist = list()

    for entry in param_list:
        lentry = entry.lower()
        if lentry.startswith('lport'):
            port = lentry.rpartition('=')[2]
            portlist.append(port)

    return portlist

class PortState(Enum):
    OPEN = 'Allow'
    CLOSE = 'Deny'

class Protocol(Enum):
    TCP = 'tcp'
    UDP = 'udp'

class FirewallMode(Enum):
    ROUTER = 'router'
    GATEWAY = 'gateway'
    HOST = 'host'

# This shi^Wthing named alterator-net-iptables is unable to work in
# multi-threaded environment
class FirewallRule:
    __alterator_command = '/usr/bin/alterator-net-iptables'

    def __init__(self, data):
        data_array = data.split('|')

        self.version = data_array[0]
        self.ports = get_ports(data_array[1:])
        self.properties = getprops(data_array[1:])

    def apply(self):
        tcp_command = []
        udp_command = []

        for port in self.ports:
            tcp_port = '{}'.format(port)
            udp_port = '{}'.format(port)

            if PortState.OPEN.value == self.properties['action']:
                tcp_port = '+' + tcp_port
                udp_port = '+' + udp_port
            if PortState.CLOSE.value == self.properties['action']:
                tcp_port = '-' + tcp_port
                udp_port = '-' + udp_port

            portcmd = [
                  self.__alterator_command
                , 'write'
                , '-m', FirewallMode.HOST.value
                , '-t', tcp_port
                , '-u', udp_port
            ]
            proc = subprocess.Popen(portcmd)
            proc.wait()

