#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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
from unittest.mock import patch, MagicMock

from gpoa_lib.frontend.appliers.control import control_subst, control


def _mock_popen(stdout_data=b'default unknown\n', stderr_data=b''):
    proc = MagicMock()
    proc.__enter__ = MagicMock(return_value=proc)
    proc.__exit__ = MagicMock(return_value=False)
    proc.stdout.readline.return_value = stdout_data
    proc.stderr.readline.return_value = stderr_data
    proc.wait.return_value = 0
    return proc


class ControlSubstTestCase(unittest.TestCase):

    def test_known_mapping_dvd_rw_format(self):
        self.assertEqual(control_subst('dvd_rw-format'), 'dvd+rw-format')

    def test_known_mapping_dvd_rw_mediainfo(self):
        self.assertEqual(control_subst('dvd_rw-mediainfo'), 'dvd+rw-mediainfo')

    def test_unknown_name_unchanged(self):
        self.assertEqual(control_subst('something-else'), 'something-else')


class ControlInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.control.subprocess.Popen')
    def test_init_with_int_value(self, mock_popen_cls):
        mock_popen_cls.return_value = _mock_popen(b'value1 value2\n')
        c = control('testctrl', 0)
        self.assertEqual(c.control_value, 0)

    @patch('gpoa_lib.frontend.appliers.control.subprocess.Popen')
    def test_init_with_str_value(self, mock_popen_cls):
        mock_popen_cls.return_value = _mock_popen(b'value1 value2\n')
        c = control('testctrl', 'value1')
        self.assertEqual(c.control_value, 'value1')


class ControlMapStatusTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.control.subprocess.Popen')
    def test_map_valid_index(self, mock_popen_cls):
        mock_popen_cls.return_value = _mock_popen(b'allow deny\n')
        c = control('testctrl', 0)
        self.assertEqual(c._map_control_status(0), 'allow')
        self.assertEqual(c._map_control_status(1), 'deny')

    @patch('gpoa_lib.frontend.appliers.control.subprocess.Popen')
    def test_map_out_of_range_returns_none(self, mock_popen_cls):
        mock_popen_cls.return_value = _mock_popen(b'allow deny\n')
        c = control('testctrl', 0)
        self.assertIsNone(c._map_control_status(99))


class ControlSetStatusTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.control.subprocess.Popen')
    def test_set_with_int_value(self, mock_popen_cls):
        mock_popen_cls.return_value = _mock_popen(b'allow deny\n')
        c = control('testctrl', 0)
        c.set_control_status()
        last_call_args = mock_popen_cls.call_args_list[-1][0][0]
        self.assertEqual(last_call_args, ['/usr/sbin/control', 'testctrl', 'allow'])

    @patch('gpoa_lib.frontend.appliers.control.subprocess.Popen')
    def test_set_with_str_value(self, mock_popen_cls):
        mock_popen_cls.return_value = _mock_popen(b'allow deny\n')
        c = control('testctrl', 'deny')
        c.set_control_status()
        last_call_args = mock_popen_cls.call_args_list[-1][0][0]
        self.assertEqual(last_call_args, ['/usr/sbin/control', 'testctrl', 'deny'])
