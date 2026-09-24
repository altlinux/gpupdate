import unittest
from unittest.mock import Mock

from gpoa_lib.applier_result import ApplierResult
from gpoa_lib.plugin.plugin import plugin
from gpoa_lib.plugin.plugin_manager import plugin_manager


class PluginIsolationTests(unittest.TestCase):
    def test_failure_does_not_suppress_later_plugin(self):
        for operation in ('set_context', 'apply', 'apply_user'):
            manager = plugin_manager.__new__(plugin_manager)
            manager.is_machine = operation != 'apply_user'
            manager.username = 'alice'
            manager.plugins_enable = True
            manager.plugins_list = None
            manager.results = []
            broken, healthy = Mock(spec=plugin), Mock(spec=plugin)
            broken.plugin_name, healthy.plugin_name = 'broken', 'healthy'
            # Context support is optional in the base API.
            broken.set_context = Mock()
            healthy.set_context = Mock()
            getattr(broken, operation).side_effect = RuntimeError('broken')
            healthy.apply.return_value = ApplierResult.applied('healthy')
            healthy.apply_user.return_value = ApplierResult.applied('healthy')
            manager.plugins = [broken, healthy]
            manager.run()
            self.assertEqual([r.status for r in manager.results], ['failed', 'applied'])

    def test_cancellation_propagates(self):
        manager = plugin_manager.__new__(plugin_manager)
        manager.plugins = [object()]
        manager._run_plugin = Mock(side_effect=KeyboardInterrupt)
        with self.assertRaises(KeyboardInterrupt):
            manager.run()
