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

import unittest
import unittest.mock
import os
import json

import util.paths


class GptShortcutsTestCase(unittest.TestCase):
    @unittest.mock.patch('util.paths.cache_dir')
    def test_shortcut_reader(self, cdir_mock):
        '''
        Test functionality to read objects from Shortcuts.xml
        '''
        cdir_mock.return_value = '/var/cache/gpupdate'

        import gpt.shortcuts
        testdata_path = '{}/test/gpt/data/Shortcuts.xml'.format(os.getcwd())
        sc = gpt.shortcuts.read_shortcuts(testdata_path)

        json_obj = json.loads(sc[0].to_json())
        self.assertIn('action', json_obj)
        self.assertEqual(json_obj['action'], 'R')
        self.assertIn('path', json_obj)
        self.assertIn('dest', json_obj)

    @unittest.mock.patch('util.paths.cache_dir')
    def test_shortcut_link(self, cdir_mock):
        '''
        Test reading shortcut with targetType=URL
        '''
        cdir_mock.return_value = '/var/cache/gpupdate'

        import gpt.shortcuts
        testdata_path = '{}/test/gpt/data/Shortcuts_link.xml'.format(os.getcwd())
        sc = gpt.shortcuts.read_shortcuts(testdata_path)

        json_obj = json.loads(sc[0].to_json())
        self.assertIn('type', json_obj)
        self.assertEqual(json_obj['type'], 'URL')
        self.assertIn('path', json_obj)

    @unittest.mock.patch('util.paths.cache_dir')
    def test_shortcut_lifecycle_disabled(self, cdir_mock):
        '''
        Test reading disabled shortcut from Shortcuts_disabled.xml
        '''
        cdir_mock.return_value = '/var/cache/gpupdate'

        import gpt.shortcuts
        testdata_path = '{}/test/gpt/data/Shortcuts_disabled.xml'.format(os.getcwd())
        sc = gpt.shortcuts.read_shortcuts(testdata_path)

        self.assertEqual(len(sc), 2)
        self.assertTrue(sc[0].disabled)
        self.assertFalse(sc[1].disabled)

    @unittest.mock.patch('util.paths.cache_dir')
    def test_shortcut_lifecycle_attributes(self, cdir_mock):
        '''
        Test reading lifecycle attributes from Shortcuts_lifecycle.xml
        '''
        cdir_mock.return_value = '/var/cache/gpupdate'

        import gpt.shortcuts
        testdata_path = '{}/test/gpt/data/Shortcuts_lifecycle.xml'.format(os.getcwd())
        sc = gpt.shortcuts.read_shortcuts(testdata_path)

        self.assertEqual(len(sc), 6)
        self.assertFalse(sc[0].disabled)
        self.assertFalse(sc[0].apply_once)

        apply_once_sc = sc[1]
        self.assertTrue(apply_once_sc.apply_once)
        self.assertTrue(apply_once_sc.bypass_errors)

        disabled_sc = sc[2]
        self.assertTrue(disabled_sc.disabled)

        remove_policy_sc = sc[3]
        self.assertTrue(remove_policy_sc.remove_policy)

        update_sc = sc[4]
        self.assertEqual(update_sc.action, 'U')

        replace_once_sc = sc[5]
        self.assertTrue(replace_once_sc.apply_once)
        self.assertEqual(replace_once_sc.action, 'R')


if __name__ == '__main__':
    unittest.main()