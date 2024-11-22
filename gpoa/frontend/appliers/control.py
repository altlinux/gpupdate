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

import subprocess
from util.logging import log

def control_subst(preg_name):
    '''
    This is a workaround for control names which can't be used in
    PReg/ADMX files.
    '''
    control_triggers = dict()
    control_triggers['dvd_rw-format'] = 'dvd+rw-format'
    control_triggers['dvd_rw-mediainfo'] = 'dvd+rw-mediainfo'
    control_triggers['dvd_rw-booktype'] = 'dvd+rw-booktype'

    result = preg_name
    if preg_name in control_triggers:
        result = control_triggers[preg_name]

    return result

class control:
    def __init__(self, name, value):
        if type(value) != int and type(value) != str:
            raise Exception('Unknown type of value for control')
        self.control_name = control_subst(name)
        self.control_value = value
        self.possible_values = self._query_control_values()
        if self.possible_values == None:
            raise Exception('Unable to query possible values')

    def _query_control_values(self):
        '''
        Query possible values from control in order to perform check of
        parameter passed to constructor.
        '''
        values = list()

        popen_call = ['/usr/sbin/control', self.control_name, 'list']
        with subprocess.Popen(popen_call, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            values = proc.stdout.readline().decode('utf-8').split()
            valErr = proc.stderr.readline().decode('utf-8')
            if valErr:
                raise ValueError(valErr)
            proc.wait()
        return values

    def _map_control_status(self, int_status):
        '''
        Get control's string value by numeric index
        '''
        try:
            str_status = self.possible_values[int_status]
        except IndexError as exc:
            logdata = dict()
            logdata['control'] = self.control_name
            logdata['value from'] = self.possible_values
            logdata['by index'] = int_status
            log('E41', )
            str_status = None

        return str_status

    def get_control_name(self):
        return self.control_name

    def get_control_status(self):
        '''
        Get current control value
        '''
        line = None

        popen_call = ['/usr/sbin/control', self.control_name]
        with subprocess.Popen(popen_call, stdout=subprocess.PIPE) as proc:
            line = proc.stdout.readline().decode('utf-8').rstrip('\n\r')
            proc.wait()

        return line

    def set_control_status(self):
        if type(self.control_value) == int:
            status = self._map_control_status(self.control_value)
            if status == None:
                logdata = dict()
                logdata['control'] = self.control_name
                logdata['inpossible values'] = self.control_value
                log('E42', logdata)
                return
        elif type(self.control_value) == str:
            if self.control_value not in self.possible_values:
                logdata = dict()
                logdata['control'] = self.control_name
                logdata['inpossible values'] = self.control_value
                log('E59', logdata)
                return
            status = self.control_value
        logdata = dict()
        logdata['control'] = self.control_name
        logdata['status'] = status
        log('D68', logdata)

        try:
            popen_call = ['/usr/sbin/control', self.control_name, status]
            with subprocess.Popen(popen_call, stdout=subprocess.PIPE) as proc:
                proc.wait()
        except:
            logdata = dict()
            logdata['control'] = self.control_name
            logdata['status'] = status
            log('E43', logdata)
