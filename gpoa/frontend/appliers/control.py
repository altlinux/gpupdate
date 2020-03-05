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
import threading
import logging
from util.logging import slogm

class control:
    def __init__(self, name, value):
        if type(value) != int and type(value) != str:
            raise Exception('Unknown type of value for control')
        self.control_name = name
        self.control_value = value
        self.possible_values = self._query_control_values()
        if self.possible_values == None:
            raise Exception('Unable to query possible values')

    def _query_control_values(self):
        proc = subprocess.Popen(['/usr/sbin/control', self.control_name, 'list'], stdout=subprocess.PIPE)
        values = list()
        for line in proc.stdout:
            values = [x.decode() for x in line.split()]
            break

        return values

    def _map_control_status(self, int_status):
        try:
            str_status = self.possible_values[int_status]
        except IndexError:
            str_status = None
        return str_status

    def get_control_name(self):
        return self.control_name

    def get_control_status(self):
        proc = subprocess.Popen(['/usr/sbin/control', self.control_name], stdout=subprocess.PIPE)
        for line in proc.stdout:
            return line.rstrip('\n\r')

    def set_control_status(self):
        if type(self.control_value) == int:
            status = self._map_control_status(self.control_value)
            if status == None:
                logging.error(slogm('\'{}\' is not in possible values for control {}'.format(self.control_value, self.control_name)))
                return
        elif type(self.control_value) == str:
            if self.control_value not in self.possible_values:
                logging.error(slogm('\'{}\' is not in possible values for control {}'.format(self.control_value, self.control_name)))
                return
            status = self.control_value

        logging.debug(slogm('Setting control {} to {}'.format(self.control_name, status)))

        try:
            proc = subprocess.Popen(['/usr/sbin/control', self.control_name, status], stdout=subprocess.PIPE)
        except:
            logging.error(slogm('Unable to set {} to {}'.format(self.control_name, status)))

