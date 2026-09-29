import importlib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gpoa_lib.plugin.plugin_manager import plugin_manager


class PackagedDMTests(unittest.TestCase):
    def manager(self, machine=True):
        manager = plugin_manager.__new__(plugin_manager)
        manager.is_machine = machine
        manager.username = None if machine else 'alice'
        manager.file_cache = Mock()
        manager.dict_dconf_db = {}
        manager.list_plugins = []
        manager.results = []
        manager.plugins_enable = True
        manager.plugins_list = None
        return manager

    def test_packaged_import_without_external_directory_and_enable_gates(self):
        manager = self.manager()
        with patch.object(Path, 'exists', return_value=False):
            manager.plugins = manager.load_plugins()
        self.assertEqual([p.plugin_name for p in manager.plugins], ['DMApplier'])
        obj = manager.plugins[0]
        self.assertIsNotNone(obj._log)
        with patch.object(obj, 'run', return_value=None) as run:
            for enabled, names, expected in ((False, None, 0), (True, [], 0),
                                              (True, ['DMApplier'], 1)):
                manager.plugins_enable, manager.plugins_list = enabled, names
                manager.run()
                self.assertEqual(run.call_count, expected)
        manager.file_cache.store.assert_not_called()

    def test_user_context_has_no_packaged_machine_plugin(self):
        manager = self.manager(False)
        with patch.object(Path, 'exists', return_value=False):
            self.assertEqual(manager.load_plugins(), [])

    def test_external_replacement_wins_by_module_or_plugin_name(self):
        for module_name in ('dm_applier', 'site_greeter'):
            manager = self.manager()
            replacement = SimpleNamespace(plugin_name='DMApplier')
            manager.list_plugins = [module_name]
            with patch.object(Path, 'exists', return_value=True), \
                    patch.object(Path, 'is_dir', return_value=True), \
                    patch.object(manager, '_load_plugins_from_directory', return_value=[replacement]), \
                    patch('gpoa_lib.plugin.plugin_manager.importlib.import_module') as load:
                self.assertEqual(manager.load_plugins(), [replacement])
                load.assert_not_called()

    def test_empty_user_factory_is_not_registered(self):
        manager = self.manager(False)
        module = importlib.import_module('gpoa_lib.frontend_plugins.dm_applier')
        self.assertIsNone(manager._instantiate_plugin(module, 'dm_applier', Path(module.__file__)))
        self.assertEqual(manager.list_plugins, [])
