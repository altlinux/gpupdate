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
    filter_dict_keys,
    flatten_dictionary,
    remove_empty_values,
    convert_string_dconf,
    update_dict,
    find_preg_type,
    get_keys_dconf_locks,
)


class FilterDictKeysAdvancedTestCase(unittest.TestCase):

    def test_empty_input(self):
        self.assertEqual(filter_dict_keys('Software/Test', {}), {})

    def test_multiple_matches(self):
        data = {
            'Software/BaseALT/a': '1',
            'Software/BaseALT/b': '2',
            'Software/Other/c': '3',
        }
        result = filter_dict_keys('Software/BaseALT', data)
        self.assertEqual(len(result), 2)

    def test_backslash_normalization(self):
        data = {r'SOFTWARE\Test\Key': 'val'}
        result = filter_dict_keys(r'SOFTWARE\Test', data)
        self.assertEqual(len(result), 1)


class FlattenDictionaryAdvancedTestCase(unittest.TestCase):

    def test_deeply_nested(self):
        data = {'a': {'b': {'c': {'d': 1}}}}
        result = flatten_dictionary(data)
        self.assertEqual(result, {'a/b/c/d': 1})

    def test_preserves_types(self):
        data = {'a': 42, 'b': 'str', 'c': True}
        result = flatten_dictionary(data)
        self.assertEqual(result['a'], 42)
        self.assertEqual(result['b'], 'str')
        self.assertEqual(result['c'], True)


class ConvertStringDconfRoundTripTestCase(unittest.TestCase):

    def test_roundtrip_sharp(self):
        original = 'test#value'
        encoded = convert_string_dconf(original)
        decoded = convert_string_dconf(encoded)
        self.assertIn('#', decoded)

    def test_roundtrip_semicolon(self):
        original = 'test;value'
        encoded = convert_string_dconf(original)
        decoded = convert_string_dconf(encoded)
        self.assertIn(';', decoded)


class UpdateDictEdgeTestCase(unittest.TestCase):

    def test_deep_merge(self):
        d1 = {'a': {'b': {'c': 1}}}
        d2 = {'a': {'b': {'d': 2}}}
        update_dict(d1, d2)
        self.assertEqual(d1['a']['b']['c'], 1)
        self.assertEqual(d1['a']['b']['d'], 2)

    def test_empty_source(self):
        d1 = {'a': 1}
        update_dict(d1, {})
        self.assertEqual(d1, {'a': 1})


class FindPregTypeEdgeTestCase(unittest.TestCase):

    def test_bool_is_int(self):
        self.assertEqual(find_preg_type(True), 4)

    def test_float_is_not_int(self):
        self.assertEqual(find_preg_type(3.14), 1)


class GetKeysDconfLocksTestCase(unittest.TestCase):

    def test_locks_filtered(self):
        data = {'Locks/Software/Test/key': 1, 'Software/Other': 0}
        result = get_keys_dconf_locks(data)
        self.assertEqual(len(result), 1)
        self.assertIn('/Software/Test/key', result[0])

    def test_nested_locks(self):
        data = {'Locks': {'Software/Test': {'key1': 1, 'key2': 1}}}
        result = get_keys_dconf_locks(data)
        self.assertEqual(len(result), 2)

    def test_no_locks(self):
        data = {'Software/Test/key': 'value'}
        result = get_keys_dconf_locks(data)
        self.assertEqual(result, [])
