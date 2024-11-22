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

import unittest

from util.preg import load_preg
from frontend.appliers.control import control

class ControlTestCase(unittest.TestCase):
    '''
    Semi-integrational tests for control facility
    '''
    def test_control_with_int(self):
        '''
        Test procedure for control framework invocation with integer
        value. The type of data loaded from PReg must be 'int' but
        we're storing all values as strings inside the database. So,
        for the test to be correct - we transform the value to string
        first.
        '''
        preg_file = 'test/frontend/appliers/data/control_int.pol'

        preg_data = load_preg(preg_file)
        for entry in preg_data.entries:
            control_name = entry.valuename
            control_value = str(entry.data)

            test_control = control(control_name, int(control_value))
            test_control.set_control_status()

    def test_control_int_out_of_range(self):
        '''
        Test procedure for control framework invocation with incorrect
        integer value (out of range). The type of data loaded from PReg
        must be 'int' but we're storing all values as strings inside the
        database. So, for the test to be correct - we transform the
        value to string first.
        '''
        control_name = 'sshd-gssapi-auth'
        control_value = '50'

        test_control = control(control_name, int(control_value))
        test_control.set_control_status()

    def test_control_with_str(self):
        '''
        Test procedure for control framework invocation with string
        value. The type of data loaded from PReg must be 'str'.
        '''
        preg_file = 'test/frontend/appliers/data/control_string.pol'

        preg_data = load_preg(preg_file)
        for entry in preg_data.entries:
            control_name = entry.valuename
            control_value = entry.data

            test_control = control(control_name, str(control_value))
            test_control.set_control_status()

