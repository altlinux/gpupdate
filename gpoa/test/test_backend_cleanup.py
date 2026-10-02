import importlib
import importlib.machinery
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class BackendCleanupTest(unittest.TestCase):
    def _controller(self):
        loader = importlib.machinery.SourceFileLoader(
            'cleanup_controller_test', str(Path(__file__).parents[1] / 'gpoa'))
        module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
        loader.exec_module(module)
        controller = module.gpoa_controller.__new__(module.gpoa_controller)
        controller.username, controller.is_machine, controller.noupdate = 'host', True, False
        controller._gpoa_controller__args = SimpleNamespace(dc=None, nodomain=False)
        return module, controller

    def test_controller_keeps_credentials_until_plugins_and_closes_on_each_failure(self):
        phases = ['retrieve', 'save', 'frontend', 'save_final', 'plugins']
        for failure in (None, *phases):
            for cleanup_failure in (False, True):
                with self.subTest(failure=failure, cleanup_failure=cleanup_failure):
                    module, controller = self._controller()
                    events = []
                    error = OSError('failed ' + str(failure))
                    def action(phase):
                        def execute(*args, **kwargs):
                            events.append(phase)
                            if phase == failure:
                                raise error
                            if phase == 'close' and cleanup_failure:
                                raise RuntimeError('cleanup failed')
                        return execute
                    backend = Mock()
                    backend.retrieve_and_store.side_effect = action('retrieve')
                    backend.close.side_effect = action('close')
                    controller.start_frontend = Mock(side_effect=action('frontend'))
                    controller.start_plugins = Mock(side_effect=action('plugins'))
                    with patch.object(module, 'get_policy_uid', return_value=None), \
                            patch.object(module, 'is_root', return_value=True), \
                            patch.object(module, 'backend_factory', return_value=backend), \
                            patch.object(module, 'save_dconf', side_effect=action('save')), \
                            patch.object(module, 'save_dconf_without_previous', side_effect=action('save_final')):
                        if failure is None:
                            controller.start_backend()
                        else:
                            with self.assertRaises(OSError) as raised:
                                controller.start_backend()
                            self.assertIs(error, raised.exception)
                    expected = phases if failure is None else phases[:phases.index(failure) + 1]
                    self.assertEqual(expected + ['close'], events)
                    backend.close.assert_called_once_with()

    def test_domain_cleanup_is_idempotent_and_safe_for_partial_objects(self):
        for name in ('freeipa_backend', 'samba_backend'):
            module = importlib.import_module('backend.' + name)
            cls = getattr(module, name)
            backend = cls.__new__(cls)
            backend.cache_path = '/owned/cache'
            with self.subTest(backend=name), patch.object(module, 'machine_kdestroy') as destroy:
                backend.close()
                destroy.assert_not_called()
                setattr(backend, '_' + name + '__kinit_successful', True)
                backend.close()
                backend.close()
                backend.__del__()
                destroy.assert_called_once_with('/owned/cache')

    def test_interpreter_shutdown_does_not_run_backend_cleanup(self):
        for name in ('freeipa_backend', 'samba_backend'):
            script = f'''
import importlib
module = importlib.import_module('backend.{name}')
def unexpected_cleanup(*args):
    raise AssertionError('late credential cleanup')
module.machine_kdestroy = unexpected_cleanup
late_owner = module.{name}.__new__(module.{name})
late_owner.cache_path = '/unused/cache'
late_owner._{name}__kinit_successful = True
'''
            with self.subTest(backend=name):
                result = subprocess.run([sys.executable, '-B', '-c', script],
                                        text=True, capture_output=True, timeout=15)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual('', result.stderr)
