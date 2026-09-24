import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


def load_setup():
    path = Path(__file__).resolve().parents[1] / 'gpupdate-setup'
    loader = importlib.machinery.SourceFileLoader('setup_under_test', str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    return module


class SetupUpdateTests(unittest.TestCase):
    def test_update_defaults_are_unspecified(self):
        module = load_setup()
        with patch('sys.argv', ['gpupdate-setup', 'update']):
            args = module.parse_arguments()
        self.assertIsNone(args.backend)
        self.assertIsNone(args.local_policy)

    def test_update_preserves_sources_but_accepts_explicit_overrides(self):
        module = load_setup()
        for backend in ('samba', 'freeipa', 'local'):
            config = Mock()
            config.get_backend.return_value = backend
            with patch.object(module, 'GPConfig', return_value=config), \
                    patch.object(module, 'get_default_policy_name', return_value='default'), \
                    patch.object(module.os.path, 'isdir', return_value=True), \
                    patch.object(module, 'validate_policy_name', return_value=True), \
                    patch.object(module, 'rollback_on_error', return_value=False):
                module.act_update(None, None)
                config.set_backend.assert_not_called()
                config.set_local_policy_template.assert_not_called()
                module.act_update('custom', 'local')
                config.set_backend.assert_called_once_with('local')
                config.set_local_policy_template.assert_called_once_with('custom')
