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
import tempfile
import unittest
import sys


class IniActionsTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        from frontend.appliers.ini_file import Ini_file
        from gpt.inifiles import inifile
        from util.arguments import action_letter2enum
        cls.Ini_file = Ini_file
        cls.inifile = inifile
        cls.action_letter2enum = action_letter2enum

    def _make_ini_obj(self, path, section='sec1', property='key1',
                      value='val1', action='C'):
        obj = self.inifile(path)
        obj.set_section(section)
        obj.set_property(property)
        obj.set_value(value)
        obj.set_action(action)
        return obj

    def _create_ini_file(self, inifile_obj, username=None, allow_empty=False,
                         allow_unquoted=False, allow_special=False,
                         skip_if_matches=False):
        return self.Ini_file(inifile_obj, username=username,
                              allow_empty_sections=allow_empty,
                              allow_unquoted_commas=allow_unquoted,
                              allow_special_chars=allow_special,
                              skip_if_matches=skip_if_matches)

    def test_create_new_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_create.ini')
            obj = self._make_ini_obj(path, 'mysection', 'mykey', 'myvalue', 'C')
            result = self._create_ini_file(obj)
            self.assertIsNotNone(result)
            self.assertTrue(result.modified)
            with open(path, 'r') as f:
                content = f.read()
            self.assertIn('mysection', content)
            self.assertIn('mykey', content)
            self.assertIn('myvalue', content)

    def test_create_existing_key_skip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_skip.ini')
            obj = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            self._create_ini_file(obj)
            obj2 = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            result2 = self._create_ini_file(obj2, skip_if_matches=True)
            self.assertFalse(result2.modified, 'skip_if_matches should skip when value matches')

    def test_create_existing_key_no_skip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_noskip.ini')
            obj = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            self._create_ini_file(obj)
            obj2 = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            result2 = self._create_ini_file(obj2, skip_if_matches=False)
            self.assertTrue(result2.modified, 'Without skip_if_matches, should always write')

    def test_replace_always_writes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_replace.ini')
            obj = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            self._create_ini_file(obj)
            obj2 = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'R')
            result2 = self._create_ini_file(obj2, skip_if_matches=True)
            self.assertTrue(result2.modified, 'REPLACE should always write even with skip_if_matches')

    def test_update_existing_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_update.ini')
            obj = self._make_ini_obj(path, 'sec1', 'key1', 'old_val', 'C')
            self._create_ini_file(obj)
            obj2 = self._make_ini_obj(path, 'sec1', 'key1', 'new_val', 'U')
            result2 = self._create_ini_file(obj2, skip_if_matches=True)
            self.assertTrue(result2.modified, 'UPDATE with different value should write')

    def test_delete_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_delete_key.ini')
            obj = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            self._create_ini_file(obj)
            obj2 = self._make_ini_obj(path, 'sec1', 'key1', action='D')
            result2 = self._create_ini_file(obj2)
            self.assertTrue(result2.modified)

    def test_delete_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_delete_sec.ini')
            obj = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            self._create_ini_file(obj)
            obj2 = self._make_ini_obj(path, 'sec1', property=None, action='D')
            result2 = self._create_ini_file(obj2)
            self.assertTrue(result2.modified)

    def test_create_no_section(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_nosec.ini')
            obj = self._make_ini_obj(path, section=None, property='nosec_key', value='nosec_val', action='C')
            result = self._create_ini_file(obj, allow_empty=True)
            self.assertTrue(result.modified)

    def test_skip_if_matches_different_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_diff_val.ini')
            obj = self._make_ini_obj(path, 'sec1', 'key1', 'old_val', 'C')
            self._create_ini_file(obj)
            obj2 = self._make_ini_obj(path, 'sec1', 'key1', 'new_val', 'U')
            result2 = self._create_ini_file(obj2, skip_if_matches=True)
            self.assertTrue(result2.modified, 'Different value should write even with skip_if_matches')

    def test_apply_once_always_writes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'test_apply_once.ini')
            obj = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            self._create_ini_file(obj)
            obj2 = self._make_ini_obj(path, 'sec1', 'key1', 'val1', 'C')
            result2 = self._create_ini_file(obj2, skip_if_matches=False)
            self.assertTrue(result2.modified, 'apply_once: skip_if_matches=False always writes')


if __name__ == '__main__':
    unittest.main()