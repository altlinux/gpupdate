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

class FirewallRule:
    def __init__(self, data):
        data_array = data.split('|')

        self.version = data_array[0]
        self.action = data_array[1]
        self.active = data_array[2]
        self.dir = data_array[3]
        self.protocol = data_array[4]
        self.profile = data_array[5]
        self.lport = data_array[6]
        self.name = data_array[7]
        self.desc = data_array[8]

    def apply(self):
        pstr = '{} {} {} {} {} {} {} {} {}'.format(self.version
            , self.action
            , self.active
            , self.dir
            , self.protocol
            , self.profile
            , self.lport
            , self.name
            , self.desc)

