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

import unittest
import os


class GptParsingTestCase(unittest.TestCase):
    DATA_DIR = os.path.join(os.getcwd(), 'test', 'gpt', 'data')

    def _data_path(self, filename):
        return os.path.join(self.DATA_DIR, filename)

    def test_parse_inifiles_lifecycle(self):
        from gpt.inifiles import read_inifiles
        items = read_inifiles(self._data_path('IniFiles_lifecycle.xml'))
        self.assertEqual(len(items), 10)

        basic = items[0]
        self.assertEqual(basic.path, '/tmp/gptest_lc_c1.ini')
        self.assertEqual(basic.section, 's1')
        self.assertEqual(basic.property, 'k1')
        self.assertEqual(basic.value, 'v1')
        self.assertEqual(basic.action, 'C')
        self.assertFalse(basic.disabled)
        self.assertFalse(basic.remove_policy)
        self.assertFalse(basic.bypass_errors)
        self.assertFalse(basic.apply_once)
        self.assertEqual(basic.uid, '{LC-INI-001}')

        apply_once = items[1]
        self.assertTrue(apply_once.apply_once)
        self.assertTrue(apply_once.bypass_errors)
        self.assertTrue(len(apply_once.filters) > 0)

        disabled = items[2]
        self.assertTrue(disabled.disabled)
        self.assertFalse(disabled.apply_once)

        remove_policy = items[3]
        self.assertTrue(remove_policy.remove_policy)
        self.assertTrue(remove_policy.bypass_errors)

        update = items[4]
        self.assertEqual(update.action, 'U')

        update_once = items[5]
        self.assertTrue(update_once.apply_once)

        delete = items[6]
        self.assertEqual(delete.action, 'D')

        replace = items[7]
        self.assertEqual(replace.action, 'R')

        replace_once = items[8]
        self.assertTrue(replace_once.apply_once)
        self.assertEqual(replace_once.action, 'R')

        no_sec = items[9]
        self.assertIsNone(no_sec.section)
        self.assertEqual(no_sec.property, 'nosec_key')

    def test_parse_inifiles_disabled(self):
        from gpt.inifiles import read_inifiles
        items = read_inifiles(self._data_path('IniFiles_disabled.xml'))
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0].disabled)
        self.assertFalse(items[1].disabled)

    def test_parse_folders_lifecycle(self):
        from gpt.folders import read_folders
        items = read_folders(self._data_path('Folders_lifecycle.xml'))
        self.assertEqual(len(items), 6)

        basic = items[0]
        self.assertEqual(basic.action, 'C')
        self.assertFalse(basic.disabled)
        self.assertEqual(basic.uid, '{LC-FOLD-001}')

        apply_once = items[1]
        self.assertTrue(apply_once.apply_once)

        disabled = items[2]
        self.assertTrue(disabled.disabled)

        remove_policy = items[3]
        self.assertTrue(remove_policy.remove_policy)
        self.assertTrue(remove_policy.bypass_errors)

        delete = items[4]
        self.assertEqual(delete.action, 'D')
        self.assertTrue(delete.delete_folder)

        replace = items[5]
        self.assertEqual(replace.action, 'R')

    def test_parse_files_lifecycle(self):
        from gpt.files import read_files
        items = read_files(self._data_path('Files_lifecycle.xml'))
        self.assertEqual(len(items), 5)

        basic = items[0]
        self.assertEqual(basic.action, 'C')
        self.assertFalse(basic.disabled)
        self.assertEqual(basic.uid, '{LC-FILE-001}')

        apply_once = items[1]
        self.assertTrue(apply_once.apply_once)

        disabled = items[2]
        self.assertTrue(disabled.disabled)

        remove_policy = items[3]
        self.assertTrue(remove_policy.remove_policy)

        replace_once = items[4]
        self.assertTrue(replace_once.apply_once)
        self.assertEqual(replace_once.action, 'R')

    def test_parse_envvars_lifecycle(self):
        from gpt.envvars import read_envvars
        items = read_envvars(self._data_path('EnvironmentVariables_lifecycle.xml'))
        self.assertEqual(len(items), 7)

        basic = items[0]
        self.assertEqual(basic.action, 'C')
        self.assertEqual(basic.name, 'GPTST_EV_C1')
        self.assertFalse(basic.disabled)
        self.assertEqual(basic.uid, '{LC-EV-001}')

        apply_once = items[1]
        self.assertTrue(apply_once.apply_once)
        self.assertTrue(apply_once.bypass_errors)

        disabled = items[2]
        self.assertTrue(disabled.disabled)

        remove_policy = items[3]
        self.assertTrue(remove_policy.remove_policy)

        update = items[4]
        self.assertEqual(update.action, 'U')

        update_once = items[5]
        self.assertTrue(update_once.apply_once)

        delete = items[6]
        self.assertEqual(delete.action, 'D')

    def test_parse_inifiles_filters(self):
        from gpt.inifiles import read_inifiles
        items = read_inifiles(self._data_path('IniFiles_filters.xml'))
        self.assertEqual(len(items), 7)

        run_once_only = items[0]
        self.assertTrue(run_once_only.apply_once)
        self.assertEqual(len(run_once_only.filters), 1)
        self.assertEqual(run_once_only.filters[0].filter_type, 'FilterRunOnce')

        run_once_with_computer = items[1]
        self.assertTrue(run_once_with_computer.apply_once)
        self.assertEqual(len(run_once_with_computer.filters), 2)
        filter_types = [f.filter_type for f in run_once_with_computer.filters]
        self.assertIn('FilterRunOnce', filter_types)
        self.assertIn('FilterComputer', filter_types)

        computer_match = items[2]
        self.assertFalse(computer_match.apply_once)
        self.assertEqual(len(computer_match.filters), 1)
        self.assertEqual(computer_match.filters[0].filter_type, 'FilterComputer')
        self.assertEqual(computer_match.filters[0].name, '__TESTHOST__')

        computer_no_match = items[3]
        self.assertEqual(computer_no_match.filters[0].name, 'NONEXISTENT_HOST')

        computer_negate = items[4]
        self.assertTrue(computer_negate.filters[0].negate)

        domain_filter = items[5]
        self.assertEqual(domain_filter.filters[0].filter_type, 'FilterDomain')

    def test_uid_from_xml_preserved(self):
        from gpt.inifiles import read_inifiles
        items = read_inifiles(self._data_path('IniFiles_lifecycle.xml'))

        for item in items:
            self.assertIsNotNone(item.uid, f'UID should not be None for {item.path}')
            self.assertTrue(item.uid.startswith('{'), f'UID should start with {{: {item.uid}')

        self.assertEqual(items[0].uid, '{LC-INI-001}')

    def test_uid_auto_generated_when_missing(self):
        from gpt.inifiles import inifile
        from util.gpp_lifecycle import generate_ini_uid
        obj = inifile('/tmp/test_uid.ini')
        obj.set_section('sec1')
        obj.set_property('k1')
        obj.set_uid(None)
        self.assertIsNotNone(obj.uid)
        self.assertTrue(obj.uid.startswith('{GENERATED-'))

    def test_changed_timestamp_conversion(self):
        from gpt.inifiles import read_inifiles
        items = read_inifiles(self._data_path('IniFiles_lifecycle.xml'))

        for item in items:
            self.assertIsNotNone(item.changed, f'changed should not be None for {item.path}')

        first = items[0]
        self.assertIn('16.04.2026', first.changed)

    def test_filter_attributes_preserved(self):
        from gpt.inifiles import read_inifiles
        items = read_inifiles(self._data_path('IniFiles_filters.xml'))

        computer_match = items[2]
        filt = computer_match.filters[0]
        self.assertEqual(filt.filter_type, 'FilterComputer')
        self.assertEqual(filt.name, '__TESTHOST__')
        self.assertEqual(filt.bool, 'AND')
        self.assertFalse(filt.negate)

    def test_parse_inifiles_disabled_attributes(self):
        from gpt.inifiles import read_inifiles
        from gpt.folders import read_folders
        from gpt.files import read_files
        from gpt.envvars import read_envvars

        ini_items = read_inifiles(self._data_path('IniFiles_disabled.xml'))
        self.assertTrue(ini_items[0].disabled)
        self.assertFalse(ini_items[1].disabled)

        fld_items = read_folders(self._data_path('Folders_disabled.xml'))
        self.assertTrue(fld_items[0].disabled)
        self.assertFalse(fld_items[1].disabled)

        file_items = read_files(self._data_path('Files_disabled.xml'))
        self.assertTrue(file_items[0].disabled)
        self.assertFalse(file_items[1].disabled)

        ev_items = read_envvars(self._data_path('EnvironmentVariables_disabled.xml'))
        self.assertTrue(ev_items[0].disabled)
        self.assertFalse(ev_items[1].disabled)


if __name__ == '__main__':
    unittest.main()