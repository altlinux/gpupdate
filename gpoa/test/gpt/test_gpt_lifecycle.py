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

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

gpoa_dir = os.path.join(os.path.dirname(__file__), '..', '..')
gpoa_dir = os.path.abspath(gpoa_dir)
if gpoa_dir not in sys.path:
    sys.path.insert(0, gpoa_dir)

from gpt.inifiles import inifile
from gpt.dynamic_attributes import DynamicAttributes
from util.gpp_lifecycle import generate_element_uid, element_to_dict


class GppLifecycleTestCase(unittest.TestCase):

    def test_mark_element_applied_sets_timestamp_on_dict(self):
        element = {'uid': '{TEST-001}', 'path': '/tmp/test.ini'}
        timestamp = '16.04.2026 12:00:00'
        element['applied'] = timestamp
        self.assertEqual(element['applied'], timestamp)
        self.assertIn('applied', element)

    def test_mark_element_applied_sets_on_original_object(self):
        obj = inifile('/tmp/test.ini')
        obj.set_section('s')
        obj.set_property('k')
        obj.set_value('v')
        obj.set_action('C')
        obj.set_uid('{TEST-OBJ-001}')

        self.assertFalse(hasattr(obj, 'applied'))

        timestamp = '16.04.2026 12:00:00'
        obj.applied = timestamp

        self.assertTrue(hasattr(obj, 'applied'))
        self.assertEqual(obj.applied, timestamp)

        d = dict(obj)
        self.assertIn('applied', d)
        self.assertEqual(d['applied'], timestamp)

    def test_element_to_dict_includes_applied(self):
        obj = inifile('/tmp/test2.ini')
        obj.set_section('s2')
        obj.set_property('k2')
        obj.set_value('v2')
        obj.set_action('C')
        obj.set_uid('{TEST-OBJ-002}')

        obj.applied = '16.04.2026 12:00:00'
        serialized = element_to_dict(obj)
        self.assertIn('applied', serialized)
        self.assertEqual(serialized['applied'], '16.04.2026 12:00:00')

    def test_toggle_sample_format(self):
        from datetime import datetime
        ts = datetime(2026, 4, 16, 10, 30, 45)
        formatted = ts.strftime('%d.%m.%Y %H:%M:%S')
        self.assertEqual(formatted, '16.04.2026 10:30:45')

    def test_disabled_element_skipping(self):
        data_path = os.path.join(os.getcwd(), 'test', 'gpt', 'data', 'IniFiles_lifecycle.xml')
        from gpt.inifiles import read_inifiles
        items = read_inifiles(data_path)
        enabled_count = sum(1 for i in items if not i.disabled)
        total_count = len(items)
        self.assertGreater(enabled_count, 0)
        self.assertLess(enabled_count, total_count)

    def test_apply_once_flag_detection(self):
        data_path = os.path.join(os.getcwd(), 'test', 'gpt', 'data', 'IniFiles_lifecycle.xml')
        from gpt.inifiles import read_inifiles
        items = read_inifiles(data_path)
        apply_once_items = [i for i in items if i.apply_once]
        self.assertGreater(len(apply_once_items), 0)

        for item in apply_once_items:
            has_run_once = any(f.filter_type == 'FilterRunOnce' for f in item.filters)
            self.assertTrue(has_run_once, f'apply_once item {item.uid} should have FilterRunOnce')

    def test_uid_from_xml_preserved(self):
        data_path = os.path.join(os.getcwd(), 'test', 'gpt', 'data', 'IniFiles_lifecycle.xml')
        from gpt.inifiles import read_inifiles
        items = read_inifiles(data_path)
        self.assertEqual(items[0].uid, '{LC-INI-001}')

    def test_uid_auto_generated_when_missing(self):
        obj = inifile('/tmp/test_uid.ini')
        obj.set_section('sec1')
        obj.set_property('k1')
        obj.set_uid(None)
        self.assertIsNotNone(obj.uid)
        self.assertTrue(obj.uid.startswith('{GENERATED-'))

    def test_generate_element_uid_deterministic(self):
        uid1 = generate_element_uid('inifile', path='/tmp/test.ini', section='s1', property='k1')
        uid2 = generate_element_uid('inifile', path='/tmp/test.ini', section='s1', property='k1')
        self.assertEqual(uid1, uid2)

    def test_generate_element_uid_unique(self):
        uid1 = generate_element_uid('inifile', path='/tmp/a.ini', section='s1', property='k1')
        uid2 = generate_element_uid('inifile', path='/tmp/b.ini', section='s1', property='k1')
        self.assertNotEqual(uid1, uid2)


if __name__ == '__main__':
    unittest.main()