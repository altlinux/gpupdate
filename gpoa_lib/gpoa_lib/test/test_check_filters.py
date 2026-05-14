#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

import datetime
import unittest
from unittest.mock import patch, mock_open, MagicMock

from gpoa_lib.util.check_filters import FilterChecker


class _FilterObj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FilterVariableTestCase(unittest.TestCase):

    @patch.dict('os.environ', {'MY_VAR': 'hello'})
    def test_variable_matches_env(self):
        filt = _FilterObj(variableName='MY_VAR', value='hello')
        self.assertTrue(FilterChecker.check_variable(filt))

    @patch.dict('os.environ', {'MY_VAR': 'hello'})
    def test_variable_mismatch_env(self):
        filt = _FilterObj(variableName='MY_VAR', value='world')
        self.assertFalse(FilterChecker.check_variable(filt))

    @patch.dict('os.environ', {}, clear=True)
    def test_variable_missing_env(self):
        filt = _FilterObj(variableName='NONEXISTENT', value='x')
        self.assertFalse(FilterChecker.check_variable(filt))

    def test_variable_empty_name_returns_true(self):
        filt = _FilterObj(variableName='', value='x')
        self.assertTrue(FilterChecker.check_variable(filt))


class FilterTimeTestCase(unittest.TestCase):

    @patch('datetime.datetime')
    def test_time_within_range(self, mock_dt):
        mock_dt.now.return_value.time.return_value = datetime.time(10, 30)
        mock_dt.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
        filt = _FilterObj(begin='09:00:00', end='12:00:00')
        self.assertTrue(FilterChecker.check_time(filt))

    @patch('datetime.datetime')
    def test_time_outside_range(self, mock_dt):
        mock_dt.now.return_value.time.return_value = datetime.time(14, 0)
        mock_dt.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
        filt = _FilterObj(begin='09:00:00', end='12:00:00')
        self.assertFalse(FilterChecker.check_time(filt))

    @patch('datetime.datetime')
    def test_time_overnight_range(self, mock_dt):
        mock_dt.now.return_value.time.return_value = datetime.time(23, 30)
        mock_dt.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)
        filt = _FilterObj(begin='22:00:00', end='06:00:00')
        self.assertTrue(FilterChecker.check_time(filt))

    def test_time_empty_begin_returns_true(self):
        filt = _FilterObj(begin='', end='12:00:00')
        self.assertTrue(FilterChecker.check_time(filt))

    def test_time_empty_end_returns_true(self):
        filt = _FilterObj(begin='09:00:00', end='')
        self.assertTrue(FilterChecker.check_time(filt))


class FilterCpuTestCase(unittest.TestCase):

    def test_cpu_meets_requirement(self):
        cpuinfo = 'processor\t: 0\ncpu MHz\t\t: 2400.000\n'
        filt = _FilterObj(speedMHz='2000')
        with patch('builtins.open', mock_open(read_data=cpuinfo)):
            self.assertTrue(FilterChecker.check_cpu(filt))

    def test_cpu_below_requirement(self):
        cpuinfo = 'processor\t: 0\ncpu MHz\t\t: 800.000\n'
        filt = _FilterObj(speedMHz='2000')
        with patch('builtins.open', mock_open(read_data=cpuinfo)):
            self.assertFalse(FilterChecker.check_cpu(filt))

    def test_cpu_empty_speed_returns_true(self):
        filt = _FilterObj(speedMHz='')
        self.assertTrue(FilterChecker.check_cpu(filt))

    def test_cpu_file_not_found(self):
        filt = _FilterObj(speedMHz='1000')
        with patch('builtins.open', side_effect=OSError('no file')):
            self.assertFalse(FilterChecker.check_cpu(filt))

    def test_cpu_uses_max_speed(self):
        cpuinfo = 'cpu MHz\t\t: 1200.000\ncpu MHz\t\t: 3600.000\n'
        filt = _FilterObj(speedMHz='3000')
        with patch('builtins.open', mock_open(read_data=cpuinfo)):
            self.assertTrue(FilterChecker.check_cpu(filt))


class FilterBatteryTestCase(unittest.TestCase):

    def test_battery_present(self):
        mock_entry = MagicMock()
        mock_entry.name = 'BAT0'
        mock_dir = MagicMock()
        mock_dir.iterdir.return_value = [mock_entry]
        filt = _FilterObj()
        with patch.object(FilterChecker, '__module__', 'gpoa_lib.util.check_filters'):
            with patch('gpoa_lib.util.check_filters.Path', return_value=mock_dir):
                self.assertTrue(FilterChecker.check_battery(filt))

    def test_battery_absent(self):
        mock_entry = MagicMock()
        mock_entry.name = 'ACAD'
        mock_dir = MagicMock()
        mock_dir.iterdir.return_value = [mock_entry]
        filt = _FilterObj()
        with patch('gpoa_lib.util.check_filters.Path', return_value=mock_dir):
            self.assertFalse(FilterChecker.check_battery(filt))

    def test_battery_oserror(self):
        mock_dir = MagicMock()
        mock_dir.iterdir.side_effect = OSError('no sysfs')
        filt = _FilterObj()
        with patch('gpoa_lib.util.check_filters.Path', return_value=mock_dir):
            self.assertFalse(FilterChecker.check_battery(filt))


class FilterDiskTestCase(unittest.TestCase):

    def test_disk_non_system_drive_returns_false(self):
        filt = _FilterObj(drive='D:', freeSpace='10')
        self.assertFalse(FilterChecker.check_disk(filt))

    def test_disk_system_drive_no_free_space_req(self):
        filt = _FilterObj(drive='%SystemDrive%', freeSpace='')
        self.assertTrue(FilterChecker.check_disk(filt))

    def test_disk_system_drive_empty_drive(self):
        filt = _FilterObj(drive='', freeSpace='10')
        self.assertFalse(FilterChecker.check_disk(filt))

    def test_disk_system_drive_enough_free(self):
        mounts = '/dev/sda1 / ext4 rw 0 0\n'
        filt = _FilterObj(drive='%SystemDrive%', freeSpace='1')
        statvfs_result = MagicMock()
        statvfs_result.f_bavail = 10 * 1024 * 1024 * 1024
        statvfs_result.f_frsize = 1
        with patch('builtins.open', mock_open(read_data=mounts)):
            with patch('os.statvfs', return_value=statvfs_result):
                self.assertTrue(FilterChecker.check_disk(filt))

    def test_disk_system_drive_not_enough_free(self):
        mounts = '/dev/sda1 / ext4 rw 0 0\n'
        filt = _FilterObj(drive='%SystemDrive%', freeSpace='500')
        statvfs_result = MagicMock()
        statvfs_result.f_bavail = 100 * 1024 * 1024 * 1024
        statvfs_result.f_frsize = 1
        with patch('builtins.open', mock_open(read_data=mounts)):
            with patch('os.statvfs', return_value=statvfs_result):
                self.assertFalse(FilterChecker.check_disk(filt))

    def test_disk_skips_pseudo_filesystems(self):
        mounts = 'tmpfs /tmp tmpfs rw 0 0\n/dev/sda1 / ext4 rw 0 0\n'
        filt = _FilterObj(drive='%SystemDrive%', freeSpace='1')
        statvfs_result = MagicMock()
        statvfs_result.f_bavail = 10 * 1024 * 1024 * 1024
        statvfs_result.f_frsize = 1
        with patch('builtins.open', mock_open(read_data=mounts)):
            with patch('os.statvfs', return_value=statvfs_result):
                self.assertTrue(FilterChecker.check_disk(filt))


class FilterLanguageTestCase(unittest.TestCase):

    def test_language_no_lcid_returns_true(self):
        filt = _FilterObj(language='')
        self.assertTrue(FilterChecker.check_language(filt))

    def test_language_unknown_lcid_returns_false(self):
        filt = _FilterObj(language='9999')
        self.assertFalse(FilterChecker.check_language(filt))

    @patch.dict('os.environ', {'LANG': 'ru_RU.UTF-8'})
    def test_language_default_matching(self):
        filt = _FilterObj(language='25', default='1', system='0')
        self.assertTrue(FilterChecker.check_language(filt))

    @patch.dict('os.environ', {'LANG': 'en_US.UTF-8'})
    def test_language_default_not_matching(self):
        filt = _FilterObj(language='25', default='1', system='0')
        self.assertFalse(FilterChecker.check_language(filt))

    def test_language_no_flags_returns_true(self):
        filt = _FilterObj(language='25', default='0', system='0')
        self.assertTrue(FilterChecker.check_language(filt))

    @patch.dict('os.environ', {'LANG': 'ru_RU.UTF-8'}, clear=True)
    def test_language_system_checks_locale_conf(self):
        filt = _FilterObj(language='25', default='0', system='1')
        locale_conf = 'LANG=ru_RU.UTF-8\n'
        with patch('builtins.open', mock_open(read_data=locale_conf)):
            self.assertTrue(FilterChecker.check_language(filt))


class FilterRamTestCase(unittest.TestCase):

    def test_ram_enough(self):
        meminfo = 'MemTotal:       16384000 kB\n'
        filt = _FilterObj(totalMB='1024')
        with patch('builtins.open', mock_open(read_data=meminfo)):
            self.assertTrue(FilterChecker.check_ram(filt))

    def test_ram_not_enough(self):
        meminfo = 'MemTotal:       512000 kB\n'
        filt = _FilterObj(totalMB='1024')
        with patch('builtins.open', mock_open(read_data=meminfo)):
            self.assertFalse(FilterChecker.check_ram(filt))

    def test_ram_empty_total_returns_false(self):
        filt = _FilterObj(totalMB='')
        self.assertFalse(FilterChecker.check_ram(filt))

    def test_ram_file_not_found(self):
        filt = _FilterObj(totalMB='1024')
        with patch('builtins.open', side_effect=OSError('no meminfo')):
            self.assertFalse(FilterChecker.check_ram(filt))


class FilterFileTestCase(unittest.TestCase):

    @patch('os.path.isfile', return_value=True)
    def test_file_exists_check_passes(self, mock_isfile):
        filt = _FilterObj(path='/etc/hosts', type='EXISTS', folder='0')
        self.assertTrue(FilterChecker.check_file(filt))

    @patch('os.path.isfile', return_value=False)
    def test_file_exists_check_fails(self, mock_isfile):
        filt = _FilterObj(path='/etc/nonexistent', type='EXISTS', folder='0')
        self.assertFalse(FilterChecker.check_file(filt))

    @patch('os.path.isdir', return_value=True)
    def test_file_folder_exists(self, mock_isdir):
        filt = _FilterObj(path='/etc', type='EXISTS', folder='1')
        self.assertTrue(FilterChecker.check_file(filt))

    @patch('os.path.isdir', return_value=False)
    def test_file_folder_not_exists(self, mock_isdir):
        filt = _FilterObj(path='/nonexistent', type='EXISTS', folder='1')
        self.assertFalse(FilterChecker.check_file(filt))

    def test_file_empty_path_returns_false(self):
        filt = _FilterObj(path='', type='EXISTS')
        self.assertFalse(FilterChecker.check_file(filt))

    def test_file_unknown_type_returns_false(self):
        filt = _FilterObj(path='/etc/hosts', type='CONTAINS', folder='0')
        self.assertFalse(FilterChecker.check_file(filt))

    @patch('os.path.isfile', return_value=True)
    def test_file_default_type_is_exists(self, mock_isfile):
        filt = _FilterObj(path='/etc/hosts', folder='0')
        self.assertTrue(FilterChecker.check_file(filt))


class FilterIpRangeTestCase(unittest.TestCase):

    def test_iprange_empty_min_returns_false(self):
        filt = _FilterObj(min='', max='0')
        self.assertFalse(FilterChecker.check_iprange(filt))

    @patch.object(FilterChecker, '_get_primary_ip', return_value='192.168.1.50')
    def test_iprange_ipv4_in_range(self, mock_ip):
        filt = _FilterObj(min='192.168.1.1', max='192.168.1.254', useIPv6='0')
        self.assertTrue(FilterChecker.check_iprange(filt))

    @patch.object(FilterChecker, '_get_primary_ip', return_value='10.0.0.50')
    def test_iprange_ipv4_outside_range(self, mock_ip):
        filt = _FilterObj(min='192.168.1.1', max='192.168.1.254', useIPv6='0')
        self.assertFalse(FilterChecker.check_iprange(filt))

    @patch.object(FilterChecker, '_get_primary_ip', return_value=None)
    def test_iprange_no_ip_returns_false(self, mock_ip):
        filt = _FilterObj(min='192.168.1.1', max='192.168.1.254', useIPv6='0')
        self.assertFalse(FilterChecker.check_iprange(filt))

    @patch.object(FilterChecker, '_get_primary_ip', return_value='2001:db8::1')
    def test_iprange_ipv6_in_network(self, mock_ip):
        filt = _FilterObj(min='2001:db8::', max='64', useIPv6='1')
        self.assertTrue(FilterChecker.check_iprange(filt))


class FilterMacRangeTestCase(unittest.TestCase):

    def test_macrange_empty_min_returns_false(self):
        filt = _FilterObj(min='', max='')
        self.assertFalse(FilterChecker.check_macrange(filt))

    def test_mac_range_uses_default_max(self):
        filt = _FilterObj(min='AA:BB:CC:DD:EE:FF', max='')
        route_data = 'Iface\tDestination\tGateway\t\tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\neth0\t00000000\t01010101\t0003\t0\t0\t100\t00000000\t0\t0\t0\n'
        mac_data = 'aa:bb:cc:dd:ee:ff\n'
        filt.max = 'AA:BB:CC:DD:EE:FF'
        filt.min = 'AA:BB:CC:DD:EE:FF'
        mock_open_route = mock_open(read_data=route_data)
        mock_open_mac = mock_open(read_data=mac_data)

        def open_side_effect(path, *args, **kwargs):
            if 'route' in str(path):
                return mock_open_route()
            return mock_open_mac()

        with patch('builtins.open', side_effect=open_side_effect):
            self.assertTrue(FilterChecker.check_macrange(filt))

    def test_mac_range_no_default_route(self):
        route_data = 'Iface\tDestination\tGateway\t\tFlags\neth0\t00010001\t01010101\t0003\n'
        filt = _FilterObj(min='AA:BB:CC:DD:EE:FF', max='AA:BB:CC:DD:EE:FF')
        with patch('builtins.open', mock_open(read_data=route_data)):
            self.assertFalse(FilterChecker.check_macrange(filt))

    def test_mac_range_oserror(self):
        filt = _FilterObj(min='AA:BB:CC:DD:EE:FF', max='AA:BB:CC:DD:EE:FF')
        with patch('builtins.open', side_effect=OSError('no file')):
            self.assertFalse(FilterChecker.check_macrange(filt))


class FilterHandlersRegistryTestCase(unittest.TestCase):

    def test_all_filter_types_registered(self):
        handlers = FilterChecker._get_handlers()
        expected = [
            'FilterComputer', 'FilterDomain', 'FilterDate', 'FilterUser',
            'FilterGroup', 'FilterVariable', 'FilterTime', 'FilterCpu',
            'FilterBattery', 'FilterDisk', 'FilterLanguage', 'FilterRam',
            'FilterFile', 'FilterIpRange', 'FilterMacRange',
        ]
        for name in expected:
            self.assertIn(name, handlers, f'{name} not registered')

    def test_handlers_are_callable(self):
        handlers = FilterChecker._get_handlers()
        for name, func in handlers.items():
            self.assertTrue(callable(func), f'{name} handler not callable')


if __name__ == '__main__':
    unittest.main()
