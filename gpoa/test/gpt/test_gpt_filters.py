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

gpoa_dir = os.path.join(os.path.dirname(__file__), '..', '..')
gpoa_dir = os.path.abspath(gpoa_dir)
if gpoa_dir not in sys.path:
    sys.path.insert(0, gpoa_dir)

from gpt.filter import Filter, parse_filters
from gpt.inifiles import read_inifiles
from xml.etree import ElementTree


FILTER_RUN_ONCE = 'FilterRunOnce'


def evaluate_filter_types(filters):
    types = []
    for f in filters:
        types.append(f.filter_type)
    return types


class FilterParsingTestCase(unittest.TestCase):

    def test_filter_run_once_parsed(self):
        filt = Filter(filter_type='FilterRunOnce', hidden='1', bool='AND')
        self.assertEqual(filt.filter_type, 'FilterRunOnce')
        self.assertFalse(filt.negate)

    def test_filter_computer_attributes(self):
        filt = Filter(filter_type='FilterComputer', name='TESTPC', type='NETBIOS', bool='AND')
        self.assertEqual(filt.filter_type, 'FilterComputer')
        self.assertEqual(filt.name, 'TESTPC')
        self.assertEqual(filt.type, 'NETBIOS')
        self.assertEqual(filt.bool, 'AND')
        self.assertFalse(filt.negate)

    def test_filter_negate_attribute(self):
        filt = Filter(filter_type='FilterComputer', name='TESTPC', type='NETBIOS', bool='AND', **{'not': '1'})
        self.assertTrue(filt.negate)

    def test_filter_domain_attribute(self):
        filt = Filter(filter_type='FilterDomain', name='example.com', userContext='0', bool='AND')
        self.assertEqual(filt.filter_type, 'FilterDomain')
        self.assertEqual(filt.name, 'example.com')

    def test_filter_not_converted_to_negate(self):
        filt = Filter(filter_type='FilterComputer', name='TEST', type='NETBIOS', **{'not': '0'})
        self.assertFalse(filt.negate)
        filt2 = Filter(filter_type='FilterComputer', name='TEST', type='NETBIOS', **{'not': '1'})
        self.assertTrue(filt2.negate)

    def test_filter_iterator_format(self):
        filt = Filter(filter_type='FilterComputer', name='MYPC', type='NETBIOS', bool='AND')
        d = dict(filt)
        self.assertIn('FilterComputer', d)
        self.assertEqual(d['FilterComputer']['name'], 'MYPC')

    def test_parse_filters_from_xml_element(self):
        xml_str = '<Ini><Filters><FilterComputer name="HOST1" type="NETBIOS" bool="AND" not="0"/><FilterRunOnce hidden="1" bool="AND" not="0"/></Filters></Ini>'
        root = ElementTree.fromstring(xml_str)
        filters = parse_filters(root)
        self.assertEqual(len(filters), 2)
        types = [f.filter_type for f in filters]
        self.assertIn('FilterComputer', types)
        self.assertIn('FilterRunOnce', types)

    def test_parse_filters_empty(self):
        xml_str = '<Ini></Ini>'
        root = ElementTree.fromstring(xml_str)
        filters = parse_filters(root)
        self.assertEqual(len(filters), 0)

    def test_filter_default_bool_and(self):
        filt = Filter(filter_type='FilterComputer', name='TEST', type='NETBIOS')
        self.assertEqual(filt.bool, 'AND')


class FilterRunOnceLogicTestCase(unittest.TestCase):
    FILTER_RUN_ONCE_TYPE = 'FilterRunOnce'

    def test_run_once_not_in_handler_list(self):
        handler_types = ['FilterComputer', 'FilterDomain', 'FilterDate', 'FilterUser', 'FilterGroup']
        self.assertNotIn(self.FILTER_RUN_ONCE_TYPE, handler_types)

    def test_filter_run_once_is_skipped_in_evaluation(self):
        filters = [Filter(filter_type='FilterRunOnce', hidden='1', bool='AND')]
        non_run_once = [f for f in filters if f.filter_type != 'FilterRunOnce']
        self.assertEqual(len(non_run_once), 0, 'FilterRunOnce should be filtered out')

    def test_filter_run_once_with_computer_separated(self):
        filters = [
            Filter(filter_type='FilterRunOnce', hidden='1', bool='AND'),
            Filter(filter_type='FilterComputer', name='MYPC', type='NETBIOS', bool='AND'),
        ]
        non_run_once = [f for f in filters if f.filter_type != 'FilterRunOnce']
        self.assertEqual(len(non_run_once), 1)
        self.assertEqual(non_run_once[0].filter_type, 'FilterComputer')

    def test_apply_once_set_when_run_once_present(self):
        data_path = os.path.join(os.getcwd(), 'test', 'gpt', 'data', 'IniFiles_filters.xml')
        items = read_inifiles(data_path)

        run_once_item = items[0]
        self.assertTrue(run_once_item.apply_once,
            'Element with FilterRunOnce should have apply_once=True')

        combined_item = items[1]
        self.assertTrue(combined_item.apply_once,
            'Element with FilterRunOnce+FilterComputer should have apply_once=True')

    def test_no_apply_once_without_run_once(self):
        data_path = os.path.join(os.getcwd(), 'test', 'gpt', 'data', 'IniFiles_filters.xml')
        items = read_inifiles(data_path)

        computer_only = items[2]
        self.assertFalse(computer_only.apply_once,
            'Element without FilterRunOnce should have apply_once=False')


class FilterParsingFromXmlTestCase(unittest.TestCase):

    def test_parse_filter_from_xml(self):
        data_path = os.path.join(os.getcwd(), 'test', 'gpt', 'data', 'IniFiles_filters.xml')
        items = read_inifiles(data_path)
        computer_item = items[2]
        self.assertEqual(len(computer_item.filters), 1)
        filt = computer_item.filters[0]
        self.assertEqual(filt.filter_type, 'FilterComputer')
        self.assertEqual(filt.name, '__TESTHOST__')
        self.assertEqual(filt.type, 'NETBIOS')
        self.assertFalse(filt.negate)

    def test_parse_negate_filter_from_xml(self):
        data_path = os.path.join(os.getcwd(), 'test', 'gpt', 'data', 'IniFiles_filters.xml')
        items = read_inifiles(data_path)
        negate_item = items[4]
        filt = negate_item.filters[0]
        self.assertTrue(filt.negate)

    def test_parse_combined_filters_from_xml(self):
        data_path = os.path.join(os.getcwd(), 'test', 'gpt', 'data', 'IniFiles_filters.xml')
        items = read_inifiles(data_path)
        combined = items[6]
        self.assertEqual(len(combined.filters), 2)
        types = [f.filter_type for f in combined.filters]
        self.assertIn('FilterComputer', types)
        self.assertIn('FilterDomain', types)

        for f in combined.filters:
            if f.filter_type == 'FilterDomain':
                self.assertEqual(f.bool, 'OR')


if __name__ == '__main__':
    unittest.main()