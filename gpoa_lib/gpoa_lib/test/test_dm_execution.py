import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gpoa_lib.frontend_plugins.dm_applier import DMApplier
from gpoa_lib.storage.fs_file_cache import fs_file_cache


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
            for policy_source in (str(source), '//dc/share/background.png',
                                  r'\\dc\share\background.png'):
                obj, cache = self.make_plugin(policy_source)
                cache.get.return_value = str(source)
                with patch.object(obj, 'generate_gdm', return_value=True):
                    result = obj.run()
                    self.assertEqual(result.status, 'applied')
                    self.assertEqual(result.applied_count, 1)
                    self.assertEqual(obj.dm_config['Greeter.Background'], str(source))
                with patch.object(obj, 'generate_gdm', return_value=False):
                    self.assertEqual(obj.run().status, 'failed')

    def test_smb_source_is_cached_before_configuring_any_display_manager(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'background.png'
            image.write_bytes(b'image')
            for dm in ('lightdm', 'gdm', 'sddm'):
                with self.subTest(dm=dm):
                    source = 'smb://dc0/regr/test.png'
                    obj, cache = self.make_plugin(source)
                    obj.detect_dm.return_value = {'available': [dm], 'active': dm}
                    cache.get.return_value = str(image)

                    def write_config(target, config_dir):
                        cache.store.assert_called_once_with(source, checked=True)
                        cache.get.assert_called_once_with(source)
                        self.assertEqual(obj.dm_config['Greeter.Background'], str(image))
                        return True

                    with patch.object(obj, 'write_config', side_effect=write_config) as write:
                        result = obj.run()
                    self.assertEqual(result.status, 'applied')
                    self.assertEqual(result.items[0].key, dm)
                    write.assert_called_once()

    def test_smb_source_uses_real_file_cache_and_preserves_old_file_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source = 'smb://dc0/regr/test.png'
            cache = fs_file_cache.__new__(fs_file_cache)
            cache.storage_uri = Path(directory)
            cache.samba_context = Mock()
            cache.samba_context.open.return_value = io.BytesIO(b'new image')
            obj, _ = self.make_plugin(source)
            obj.file_cache = cache
            cached = Path(directory) / 'dc0/regr/test.png'
            with patch.object(obj, 'write_config', return_value=True) as write:
                self.assertEqual(obj.run().status, 'applied')
                write.assert_called_once()
            cache.samba_context.open.assert_called_once_with(source, os.O_RDONLY)
            self.assertEqual(obj.dm_config['Greeter.Background'], str(cached))
            self.assertEqual(cached.read_bytes(), b'new image')

            cache.samba_context.open.side_effect = OSError('SMB server offline')
            with patch.object(obj, 'write_config') as write:
                self.assertEqual(obj.run().status, 'failed')
                write.assert_not_called()
            self.assertEqual(cached.read_bytes(), b'new image')
            self.assertEqual(list(cached.parent.iterdir()), [cached])

    def test_smb_requires_cache_and_existing_download_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            for cache_value in (None, str(Path(directory) / 'missing.png')):
                with self.subTest(cache_value=cache_value):
                    obj, cache = self.make_plugin('smb://dc0/regr/test.png')
                    cache.get.return_value = cache_value
                    with patch.object(obj, 'write_config') as write:
                        self.assertEqual(obj.run().status, 'failed')
                        cache.store.assert_called_once_with(
                            'smb://dc0/regr/test.png', checked=True)
                        write.assert_not_called()
            obj, _ = self.make_plugin('smb://dc0/regr/test.png')
            obj.file_cache = None
            with patch.object(obj, 'write_config') as write:
                self.assertEqual(obj.run().status, 'failed')
                write.assert_not_called()

    def test_restore_is_separate_from_source_preparation(self):
        obj, cache = self.make_plugin('backup')
        with patch.object(obj, '_restore_gdm_backup', return_value=True):
            self.assertEqual(obj.run().items[0].action, 'restore')
        cache.store.assert_not_called()
        with patch.object(obj, '_prepare_conf') as config:
            self.assertFalse(obj._generate_gdm_fallback('/unused', '/image'))
            config.assert_not_called()
