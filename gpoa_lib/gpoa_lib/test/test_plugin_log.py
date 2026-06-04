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

import gettext
import logging
import unittest
from unittest.mock import MagicMock, patch, call

from gpoa_lib.plugin.plugin_log import PluginLog


TEST_MESSAGES = {
    'i': {1: 'Info message {name}', 2: 'Simple info'},
    'w': {1: 'Warning {thing}'},
    'e': {1: 'Error {code}'},
    'd': {1: 'Debug {detail}'},
    'f': {1: 'Fatal {reason}'},
}


class PluginLogInitTestCase(unittest.TestCase):

    @patch.object(PluginLog, '_load_translations')
    def test_stores_message_dict(self, mock_load):
        p = PluginLog(message_dict=TEST_MESSAGES, locale_dir='/tmp', domain='test')
        self.assertEqual(p.message_dict, TEST_MESSAGES)

    @patch.object(PluginLog, '_load_translations')
    def test_default_message_dict_empty(self, mock_load):
        p = PluginLog(locale_dir='/tmp')
        self.assertEqual(p.message_dict, {})

    @patch.object(PluginLog, '_load_translations')
    def test_default_domain(self, mock_load):
        p = PluginLog(locale_dir='/tmp')
        self.assertEqual(p.domain, 'plugin')

    @patch.object(PluginLog, '_load_translations')
    def test_custom_domain(self, mock_load):
        p = PluginLog(locale_dir='/tmp', domain='my_plugin')
        self.assertEqual(p.domain, 'my_plugin')

    @patch.object(PluginLog, '_load_translations')
    def test_plugin_name_stored(self, mock_load):
        p = PluginLog(locale_dir='/tmp', plugin_name='TestPlugin')
        self.assertEqual(p.plugin_name, 'TestPlugin')

    @patch('gpoa_lib.plugin.plugin_log.register_plugin_messages')
    @patch.object(PluginLog, '_load_translations')
    def test_registers_flat_messages(self, mock_load, mock_register):
        PluginLog(message_dict=TEST_MESSAGES, locale_dir='/tmp', domain='test')
        mock_register.assert_called_once()
        domain_arg, flat = mock_register.call_args[0]
        self.assertEqual(domain_arg, 'test')
        self.assertIn(1, flat)
        self.assertIn(2, flat)
        self.assertEqual(flat[2], 'Simple info')

    @patch.object(PluginLog, '_load_translations')
    def test_locale_dir_set(self, mock_load):
        p = PluginLog(locale_dir='/some/path')
        self.assertEqual(p.locale_dir, '/some/path')


class PluginLogFormatTestCase(unittest.TestCase):

    @patch.object(PluginLog, '_load_translations')
    def setUp(self, mock_load):
        self.p = PluginLog(
            message_dict=TEST_MESSAGES,
            locale_dir='/tmp',
            domain='test',
            plugin_name='TestPlugin',
        )
        self.p._translation = gettext.NullTranslations()

    def test_format_message_with_data(self):
        msg = self.p._format_message('i', 1, {'name': 'world'})
        self.assertEqual(msg, 'Info message world')

    def test_format_message_without_data(self):
        msg = self.p._format_message('i', 2)
        self.assertEqual(msg, 'Simple info')

    def test_format_message_unknown_code(self):
        msg = self.p._format_message('i', 999)
        self.assertIn('Unknown message', msg)

    def test_get_full_code(self):
        code = self.p._get_full_code('W', 1)
        self.assertEqual(code, 'W00001')


class PluginLogCallTestCase(unittest.TestCase):

    @patch.object(PluginLog, '_load_translations')
    def setUp(self, mock_load):
        self.p = PluginLog(
            message_dict=TEST_MESSAGES,
            locale_dir='/tmp',
            domain='test',
            plugin_name='TestPlugin',
        )
        self.p._translation = gettext.NullTranslations()

    @patch('gpoa_lib.plugin.plugin_log.logging')
    def test_call_info(self, mock_logging):
        self.p('I1', {'name': 'test'})
        mock_logging.info.assert_called_once()

    @patch('gpoa_lib.plugin.plugin_log.logging')
    def test_call_warning(self, mock_logging):
        self.p('W1', {'thing': 'broken'})
        mock_logging.warning.assert_called_once()

    @patch('gpoa_lib.plugin.plugin_log.logging')
    def test_call_error(self, mock_logging):
        self.p('E1', {'code': '500'})
        mock_logging.error.assert_called_once()

    @patch('gpoa_lib.plugin.plugin_log.logging')
    def test_call_debug(self, mock_logging):
        self.p('D1', {'detail': 'trace'})
        mock_logging.debug.assert_called_once()

    @patch('gpoa_lib.plugin.plugin_log.logging')
    def test_call_fatal(self, mock_logging):
        self.p('F1', {'reason': 'crash'})
        mock_logging.fatal.assert_called_once()

    @patch('gpoa_lib.plugin.plugin_log.logging')
    def test_call_empty_code(self, mock_logging):
        self.p('')
        mock_logging.error.assert_called_once()

    @patch('gpoa_lib.plugin.plugin_log.logging')
    def test_call_invalid_code(self, mock_logging):
        self.p('Xabc')
        mock_logging.error.assert_called_once()


class PluginLogConvenienceMethodsTestCase(unittest.TestCase):

    @patch.object(PluginLog, '_load_translations')
    def setUp(self, mock_load):
        self.p = PluginLog(
            message_dict=TEST_MESSAGES,
            locale_dir='/tmp',
            domain='test',
            plugin_name='TestPlugin',
        )
        self.p._translation = gettext.NullTranslations()

    @patch.object(PluginLog, '__call__')
    def test_info_method(self, mock_call):
        self.p.info(1, {'name': 'x'})
        mock_call.assert_called_once_with('I1', {'name': 'x'})

    @patch.object(PluginLog, '__call__')
    def test_warning_method(self, mock_call):
        self.p.warning(1, {'thing': 'y'})
        mock_call.assert_called_once_with('W1', {'thing': 'y'})

    @patch.object(PluginLog, '__call__')
    def test_error_method(self, mock_call):
        self.p.error(1, {'code': 'z'})
        mock_call.assert_called_once_with('E1', {'code': 'z'})

    @patch.object(PluginLog, '__call__')
    def test_debug_method(self, mock_call):
        self.p.debug(1, {'detail': 'd'})
        mock_call.assert_called_once_with('D1', {'detail': 'd'})

    @patch.object(PluginLog, '__call__')
    def test_fatal_method(self, mock_call):
        self.p.fatal(1, {'reason': 'r'})
        mock_call.assert_called_once_with('F1', {'reason': 'r'})
