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
from unittest.mock import MagicMock, patch

from gpoa_lib.plugin.plugin_base import FrontendPlugin


class ConcretePlugin(FrontendPlugin):
    run_called = False
    run_kwargs = None

    def run(self, **kwargs):
        self.run_called = True
        self.run_kwargs = kwargs


class FrontendPluginAbstractTestCase(unittest.TestCase):

    def test_cannot_instantiate_directly(self):
        with self.assertRaises(TypeError):
            FrontendPlugin()

    def test_concrete_subclass_instantiates(self):
        p = ConcretePlugin()
        self.assertIsNotNone(p)

    def test_run_must_be_implemented(self):
        class IncompletePlugin(FrontendPlugin):
            pass

        with self.assertRaises(TypeError):
            IncompletePlugin()


class FrontendPluginInitTestCase(unittest.TestCase):

    def test_defaults(self):
        p = ConcretePlugin()
        self.assertEqual(p.dict_dconf_db, {})
        self.assertIsNone(p.username)
        self.assertIsNone(p.file_cache)
        self.assertIsNone(p._registry_path)

    def test_with_all_params(self):
        cache = MagicMock()
        p = ConcretePlugin(
            dict_dconf_db={'key': 'val'},
            username='testuser',
            fs_file_cache=cache,
            registry_path='Software/Test',
        )
        self.assertEqual(p.dict_dconf_db, {'key': 'val'})
        self.assertEqual(p.username, 'testuser')
        self.assertIs(p.file_cache, cache)
        self.assertEqual(p._registry_path, 'Software/Test')

    def test_none_dict_becomes_empty(self):
        p = ConcretePlugin(dict_dconf_db=None)
        self.assertEqual(p.dict_dconf_db, {})

    def test_plugin_name_is_class_name(self):
        p = ConcretePlugin()
        self.assertEqual(p.plugin_name, 'ConcretePlugin')


class FrontendPluginApplyTestCase(unittest.TestCase):

    def test_apply_calls_run(self):
        p = ConcretePlugin()
        p.apply()
        self.assertTrue(p.run_called)

    def test_apply_forwards_kwargs(self):
        p = ConcretePlugin()
        p.apply(foo='bar')
        self.assertEqual(p.run_kwargs, {'foo': 'bar'})


class FrontendPluginRegistryTestCase(unittest.TestCase):

    @patch('gpoa_lib.plugin.plugin.string_to_literal_eval', side_effect=lambda x: x)
    def test_get_dict_registry_returns_value(self, mock_eval):
        p = ConcretePlugin(dict_dconf_db={'Software/Test': {'a': 1}})
        result = p.get_dict_registry('Software/Test')
        self.assertEqual(result, {'a': 1})

    @patch('gpoa_lib.plugin.plugin.string_to_literal_eval', side_effect=lambda x: x)
    def test_get_dict_registry_missing_prefix(self, mock_eval):
        p = ConcretePlugin(dict_dconf_db={})
        result = p.get_dict_registry('Software/Missing')
        self.assertEqual(result, {})


class FrontendPluginLogTestCase(unittest.TestCase):

    @patch('gpoa_lib.plugin.plugin.PluginLog')
    def test_init_plugin_log(self, mock_plug_cls):
        p = ConcretePlugin()
        p._init_plugin_log({'i': {1: 'hello'}}, domain='test')
        mock_plug_cls.assert_called_once_with(
            {'i': {1: 'hello'}}, None, 'test', 'ConcretePlugin',
        )

    @patch('gpoa_lib.plugin.plugin.log')
    def test_log_without_init_falls_back(self, mock_log):
        p = ConcretePlugin()
        p._log = None
        p.log('W1', {'info': 'data'})
        mock_log.assert_called_once()
        args = mock_log.call_args[0]
        self.assertEqual(args[0], 'W')


class DMApplierFactoryTestCase(unittest.TestCase):

    def test_create_machine_applier_returns_instance(self):
        from gpoa_lib.frontend_plugins.dm_applier import create_machine_applier
        result = create_machine_applier({'Software/Test': {}})
        self.assertIsNotNone(result)

    def test_create_user_applier_returns_none(self):
        from gpoa_lib.frontend_plugins.dm_applier import create_user_applier
        result = create_user_applier({'Software/Test': {}})
        self.assertIsNone(result)
