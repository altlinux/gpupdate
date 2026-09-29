import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gpoa_lib.frontend_plugins.dm_applier import DMApplier


class DMExecutionTests(unittest.TestCase):
    def make_plugin(self, source):
        cache = Mock()
        obj = DMApplier({'Software/BaseALT/Policies/DisplayManager':
                         {'Greeter.Background': source}}, fs_file_cache=cache)
        cache.store.assert_not_called()
        obj.detect_dm = Mock(return_value={'available': ['gdm'], 'active': 'gdm'})
        return obj, cache

    def test_empty_disabled_and_missing_sources_do_not_write(self):
        for source, expected in ((None, 'skipped'), ('/missing/gdm-background', 'failed')):
            obj, cache = self.make_plugin(source)
            with patch.object(obj, 'write_config') as write:
                self.assertEqual(obj.run().status, expected)
                write.assert_not_called()
                cache.store.assert_not_called()

    def test_checked_unc_failure_does_not_use_stale_cached_background(self):
        obj, cache = self.make_plugin(r'\\dc\share\background.png')
        cache.store.side_effect = OSError('offline')
        cache.get.return_value = '/old/background.png'
        with patch.object(obj, 'write_config') as write:
            self.assertEqual(obj.run().status, 'failed')
            cache.store.assert_called_once_with('//dc/share/background.png', checked=True)
            cache.get.assert_not_called()
            write.assert_not_called()

    def test_local_and_unc_success_and_false_generator_result(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'background.png'
            source.write_bytes(b'image')
            for policy_source in (str(source), '//dc/share/background.png'):
                obj, cache = self.make_plugin(policy_source)
                cache.get.return_value = str(source)
                with patch.object(obj, 'generate_gdm', return_value=True):
                    result = obj.run()
                    self.assertEqual(result.status, 'applied')
                    self.assertEqual(result.applied_count, 1)
                    self.assertEqual(obj.dm_config['Greeter.Background'], str(source))
                with patch.object(obj, 'generate_gdm', return_value=False):
                    self.assertEqual(obj.run().status, 'failed')

    def test_restore_is_separate_from_source_preparation(self):
        obj, cache = self.make_plugin('backup')
        with patch.object(obj, '_restore_gdm_backup', return_value=True):
            self.assertEqual(obj.run().items[0].action, 'restore')
        cache.store.assert_not_called()
        with patch.object(obj, '_prepare_conf') as config:
            self.assertFalse(obj._generate_gdm_fallback('/unused', '/image'))
            config.assert_not_called()
