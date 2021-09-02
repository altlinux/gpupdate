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


import optparse
import socket
from samba import getopt as options


class smbopts:

    def __init__(self, prog=None):
        self.parser = optparse.OptionParser(prog)
        self.sambaopts = options.SambaOptions(self.parser)
        self.lp = self.sambaopts.get_loadparm()

    def get_realm(self):
        '''
        Get the default realm specified in smb.conf file.
        '''
        return self._get_prop('realm')

    def get_cache_dir(self):
        return self._get_prop('cache directory')

    def get_server_role(self):
        return self._get_prop('server role')

    def get_machine_name(self):
        '''
        Get localhost name looking like DC0$
        '''
        nb_name = self.get_netbios_name()
        result = nb_name + "$"

        if result == '':
            result = socket.gethostname().split('.', 1)[0].upper() + "$"

        return result

    def get_netbios_name(self):
        return self._get_prop('netbios name')

    def _get_prop(self, property_name):
        return self.lp.get(property_name)
