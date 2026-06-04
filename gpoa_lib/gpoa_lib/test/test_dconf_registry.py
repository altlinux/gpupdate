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

from gpoa_lib.storage.dconf_registry import (
    Dconf_registry,
    PregDconf,
    gplist,
    filter_dict_keys,
    find_preg_type,
    update_dict,
    convert_string_dconf,
    remove_empty_values,
    flatten_dictionary,
)


class PregDconfTestCase(unittest.TestCase):

    def test_attributes(self):
        p = PregDconf('Software/Key', 'valuename', 1, 'data')
        self.assertEqual(p.keyname, 'Software/Key')
        self.assertEqual(p.valuename, 'valuename')
        self.assertEqual(p.hive_key, 'Software/Key/valuename')
        self.assertEqual(p.type, 1)
        self.assertEqual(p.data, 'data')


class GplistTestCase(unittest.TestCase):

    def test_first_returns_element(self):
        gl = gplist([1, 2, 3])
        self.assertEqual(gl.first(), 1)

    def test_first_empty_list(self):
        gl = gplist()
        self.assertIsNone(gl.first())

    def test_count(self):
        gl = gplist([1, 2, 3])
        self.assertEqual(gl.count(), 3)

    def test_count_empty(self):
        gl = gplist()
        self.assertEqual(gl.count(), 0)


class DconfRegistryStateTestCase(unittest.TestCase):

    def setUp(self):
        Dconf_registry._info = {}
        Dconf_registry.global_registry_dict = {Dconf_registry._GpoPriority: {}}
        Dconf_registry.shortcuts = []
        Dconf_registry.folders = []
        Dconf_registry.files = []
        Dconf_registry.drives = []
        Dconf_registry.environmentvariables = []
        Dconf_registry.inifiles = []
        Dconf_registry.scripts = []
        Dconf_registry.printers = []
        Dconf_registry.networkshares = []

    def test_set_get_info(self):
        Dconf_registry.set_info('key1', 'value1')
        self.assertEqual(Dconf_registry.get_info('key1'), 'value1')

    def test_get_info_missing(self):
        self.assertIsNone(Dconf_registry.get_info('nonexistent'))

    def test_wipe_hklm(self):
        Dconf_registry.global_registry_dict['test'] = 'data'
        Dconf_registry.wipe_hklm()
        keys = list(Dconf_registry.global_registry_dict.keys())
        self.assertEqual(len(keys), 1)
        self.assertIn(Dconf_registry._GpoPriority, keys)

    def test_wipe_user_delegates(self):
        Dconf_registry.global_registry_dict['test'] = 'data'
        Dconf_registry.wipe_user()
        keys = list(Dconf_registry.global_registry_dict.keys())
        self.assertEqual(len(keys), 1)


class DconfRegistryFilterTestCase(unittest.TestCase):

    def setUp(self):
        Dconf_registry.global_registry_dict = {
            Dconf_registry._GpoPriority: {},
            'Software/BaseALT/Policies/Control': {
                'sshd-gssapi-auth': '1',
                'writeable': '0',
            },
            'Software/BaseALT/Policies/KDE': {
                'wallpaper': '/usr/share/wallpapers/test',
            },
        }

    def test_filter_entries_prefix(self):
        result = Dconf_registry.filter_entries('Software/BaseALT/Policies/Control')
        self.assertTrue(len(result) > 0)

    def test_filter_hklm_returns_gplist(self):
        result = Dconf_registry.filter_hklm_entries('Software/BaseALT/Policies/Control')
        self.assertIsInstance(result, gplist)

    def test_filter_hklm_returns_pregdconf(self):
        result = Dconf_registry.filter_hklm_entries('Software/BaseALT/Policies/Control')
        if result:
            self.assertIsInstance(result[0], PregDconf)

    def test_filter_entries_no_match(self):
        result = Dconf_registry.filter_entries('Software/Nonexistent')
        self.assertEqual(len(result), 0)

    def test_get_entry_found(self):
        Dconf_registry._gpt_read_flag = True
        result = Dconf_registry.get_entry('Software/BaseALT/Policies/Control/sshd-gssapi-auth')
        self.assertIsNotNone(result)

    def test_get_entry_not_found(self):
        Dconf_registry._gpt_read_flag = True
        result = Dconf_registry.get_entry('Software/Nonexistent/key')
        self.assertIsNone(result)

    def test_check_enable_key_true(self):
        Dconf_registry._gpt_read_flag = True
        Dconf_registry.global_registry_dict['Software/Test'] = {'enabled': '1'}
        self.assertTrue(Dconf_registry.check_enable_key('Software/Test/enabled'))

    def test_check_enable_key_false(self):
        Dconf_registry._gpt_read_flag = True
        Dconf_registry.global_registry_dict['Software/Test'] = {'enabled': '0'}
        self.assertFalse(Dconf_registry.check_enable_key('Software/Test/enabled'))

    def tearDown(self):
        Dconf_registry._gpt_read_flag = False


class DconfRegistryAddGetTestCase(unittest.TestCase):

    def setUp(self):
        Dconf_registry.shortcuts = []
        Dconf_registry.folders = []
        Dconf_registry.files = []
        Dconf_registry.environmentvariables = []

    def test_add_and_get_shortcut(self):
        obj = type('Obj', (), {'path': '/test', 'disabled': False, 'filters': []})()
        Dconf_registry.add_shortcut(obj, 'TestPolicy')
        result = Dconf_registry.get_shortcuts()
        self.assertEqual(len(result), 1)

    def test_add_and_get_folder(self):
        obj = type('Obj', (), {'path': '/tmp/test', 'disabled': False, 'filters': []})()
        Dconf_registry.add_folder(obj, 'TestPolicy')
        result = Dconf_registry.get_folders()
        self.assertEqual(len(result), 1)

    def test_add_and_get_files(self):
        obj = type('Obj', (), {'path': '/tmp/file', 'disabled': False, 'filters': []})()
        Dconf_registry.add_file(obj, 'TestPolicy')
        result = Dconf_registry.get_files()
        self.assertEqual(len(result), 1)

    def test_add_and_get_envvars(self):
        obj = type('Obj', (), {'name': 'TEST', 'disabled': False, 'filters': []})()
        Dconf_registry.add_envvar(obj, 'TestPolicy')
        result = Dconf_registry.get_envvars()
        self.assertEqual(len(result), 1)

    def test_get_scripts_by_action(self):
        obj_startup = type('Obj', (), {'action': 'STARTUP', 'path': '/test'})()
        obj_logon = type('Obj', (), {'action': 'LOGON', 'path': '/test'})()
        Dconf_registry.add_script(obj_startup, 'TestPolicy')
        Dconf_registry.add_script(obj_logon, 'TestPolicy')
        startup = Dconf_registry.get_scripts('STARTUP')
        logon = Dconf_registry.get_scripts('LOGON')
        self.assertEqual(len(startup), 1)
        self.assertEqual(len(logon), 1)


class FilterDictKeysTestCase(unittest.TestCase):

    def test_exact_prefix(self):
        data = {
            'Software/BaseALT/Policies/Control/key1': 'val1',
            'Software/Other/key2': 'val2',
        }
        result = filter_dict_keys('Software/BaseALT/Policies/Control', data)
        self.assertEqual(len(result), 1)
        self.assertIn('Software/BaseALT/Policies/Control/key1', result)

    def test_no_match(self):
        data = {'Software/Other/key': 'val'}
        result = filter_dict_keys('Software/BaseALT', data)
        self.assertEqual(len(result), 0)

    def test_backslash_path(self):
        data = {r'SOFTWARE\BaseALT\Policies\Control\key': 'val'}
        result = filter_dict_keys(r'SOFTWARE\BaseALT\Policies\Control', data)
        self.assertEqual(len(result), 1)


class FindPregTypeTestCase(unittest.TestCase):

    def test_int_returns_4(self):
        self.assertEqual(find_preg_type(42), 4)

    def test_str_returns_1(self):
        self.assertEqual(find_preg_type('hello'), 1)


class UpdateDictTestCase(unittest.TestCase):

    def test_merge_nested(self):
        d1 = {'a': {'b': 1}}
        d2 = {'a': {'c': 2}}
        update_dict(d1, d2)
        self.assertEqual(d1, {'a': {'b': 1, 'c': 2}})

    def test_overwrite_value(self):
        d1 = {'a': 1}
        d2 = {'a': 2}
        update_dict(d1, d2)
        self.assertEqual(d1['a'], 2)

    def test_new_key(self):
        d1 = {'a': 1}
        d2 = {'b': 2}
        update_dict(d1, d2)
        self.assertEqual(d1['b'], 2)

    def test_merge_lists(self):
        d1 = {'a': [1, 2]}
        d2 = {'a': [2, 3]}
        update_dict(d1, d2)
        self.assertIn(3, d1['a'])


class ConvertStringDconfTestCase(unittest.TestCase):

    def test_sharp(self):
        self.assertIn('%sharp%', convert_string_dconf('test#value'))

    def test_semicolon(self):
        self.assertIn('%semicolon%', convert_string_dconf('test;value'))

    def test_double_slash(self):
        result = convert_string_dconf('test//value')
        self.assertNotIn('//', result)

    def test_single_slash(self):
        self.assertIn('%oneslash%', convert_string_dconf('test/value'))

    def test_reverse_sharp(self):
        self.assertEqual(convert_string_dconf('test%sharp%value'), 'test#value')

    def test_no_change(self):
        self.assertEqual(convert_string_dconf('plain'), 'plain')


class RemoveEmptyValuesTestCase(unittest.TestCase):

    def test_removes_empty_strings(self):
        self.assertEqual(remove_empty_values(['a', '', 'b', '']), ['a', 'b'])

    def test_removes_none(self):
        self.assertEqual(remove_empty_values([1, None, 2]), [1, 2])

    def test_empty_input(self):
        self.assertEqual(remove_empty_values([]), [])


class FlattenDictionaryTestCase(unittest.TestCase):

    def test_flat(self):
        data = {'a': {'b': {'c': 1}}, 'd': 2}
        result = flatten_dictionary(data)
        self.assertEqual(result, {'a/b/c': 1, 'd': 2})

    def test_empty(self):
        self.assertEqual(flatten_dictionary({}), {})

    def test_single_level(self):
        data = {'key': 'value'}
        self.assertEqual(flatten_dictionary(data), {'key': 'value'})
