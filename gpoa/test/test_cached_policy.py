import importlib.machinery
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from gpt.cached import load_cached_policy
from storage.dconf_registry import Dconf_registry
from gpt.files import fileentry


class CachedPolicyTests(unittest.TestCase):
    def tearDown(self):
        Dconf_registry.reset()

    def test_hydration_keeps_current_and_previous_preferences_consistent(self):
        prefix = 'Software/BaseALT/Policies/Preferences/user'
        data = {prefix: {'Files': "[{'uid': 'f', 'fromPath': '/source', 'apply_once': True, 'applied': 'stamp'}]"}}
        with patch.object(Dconf_registry, 'get_dictionary_from_dconf_file_db', return_value=data):
            load_cached_policy('user', 1234, False)
        self.assertIsInstance(Dconf_registry.files[0], fileentry)
        self.assertEqual(Dconf_registry.files[0].applied, 'stamp')
        self.assertEqual(Dconf_registry.global_registry_dict[prefix], Dconf_registry.global_registry_dict['Previous/' + prefix])

    def test_cached_controller_does_not_construct_backend_or_save(self):
        loader = importlib.machinery.SourceFileLoader('cached_controller_test', str(Path(__file__).parents[1] / 'gpoa'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        controller = module.gpoa_controller.__new__(module.gpoa_controller)
        controller.username, controller.is_machine, controller.noupdate = 'user', False, True
        controller._gpoa_controller__args = SimpleNamespace(dc=None)
        controller.start_frontend, controller.start_plugins = Mock(), Mock()
        with patch.object(module, 'get_policy_uid', return_value=1234), patch.object(module, 'is_root', return_value=True), \
                patch.object(module, 'backend_factory') as backend, patch.object(module, 'save_dconf') as save, \
                patch('gpt.cached.load_cached_policy') as load:
            controller.start_backend()
            backend.assert_not_called()
            save.assert_not_called()
            load.assert_called_once_with('user', 1234, False)
            controller.start_frontend.assert_called_once()
            controller.start_plugins.assert_called_once()
