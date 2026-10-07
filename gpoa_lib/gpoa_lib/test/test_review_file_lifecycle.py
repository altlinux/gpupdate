import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch, Mock

from gpoa_lib.storage.gpp_state import cleanup_file, GppStateManager
from gpoa_lib.frontend.appliers.folder import remove_dir_tree
from gpoa_lib.frontend.appliers.file_cp import Files_cp


class ReviewFileLifecycleTest(TestCase):
    def test_cleanup_uses_only_manifest_and_old_wildcard_is_deferred(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            managed, other = root / 'managed.pub', root / 'unrelated.pub'
            managed.write_text('managed')
            other.write_text('sentinel')
            item = {'targetPath': directory + '/', 'fromPath': '/source/*.pub'}
            cleanup_file(item)
            self.assertTrue(managed.exists())
            cleanup_file(dict(item, managed_targets=[str(managed)]))
            self.assertFalse(managed.exists())
            self.assertEqual(other.read_text(), 'sentinel')
            with self.assertRaises(ValueError):
                cleanup_file(dict(item, managed_targets=['/etc/passwd']))

    def test_folder_target_regular_file_is_preserved(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'file'
            target.write_text('sentinel')
            for files in (False, True):
                with self.assertRaises(NotADirectoryError):
                    remove_dir_tree(target, files, True, True)
                self.assertEqual(target.read_text(), 'sentinel')

    def test_apply_once_never_borrows_known_other_policy(self):
        previous = {'uid': 'same', 'policy_guid': 'A', 'applied': 'stamp'}
        for guid, expected in [('A', True), ('B', False), (None, False)]:
            current = {'uid': 'same', 'policy_guid': guid, 'apply_once': True}
            with patch('gpoa_lib.storage.gpp_state.get_previous_elements', return_value=[previous]):
                self.assertEqual(GppStateManager().should_skip(current, 'Files'), expected)
            self.assertEqual('applied' in current, expected)

    def test_delete_never_lists_unavailable_source(self):
        module = importlib.import_module('gpoa_lib.frontend.appliers.file_cp')
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'target'
            target.write_text('old')
            item = SimpleNamespace(targetPath=str(target), fromPath='//server/share/*.pub',
                                   action='D', readOnly=False, archive=False, hidden=False,
                                   suppress=False, executable=False)
            cache = Mock()
            cache.get_ls_smbdir.side_effect = OSError('offline')
            with patch.object(module, 'expand_windows_var', side_effect=lambda value, user: value):
                Files_cp(item, cache, Mock())
            self.assertFalse(target.exists())
            cache.get_ls_smbdir.assert_not_called()

    def test_copied_manifest_survives_refresh(self):
        module = importlib.import_module('gpoa_lib.frontend.appliers.file_cp')
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / 'source.pub', root / 'out'
            source.write_text('public')
            destination.mkdir()
            item = SimpleNamespace(targetPath=str(destination) + '/', fromPath=str(source),
                                   action='C', readOnly=False, archive=False, hidden=False,
                                   suppress=False, executable=False)
            exe = Mock()
            exe.get_list_markers.return_value = []
            with patch.object(module, 'expand_windows_var', side_effect=lambda value, user: value):
                Files_cp(item, Mock(), exe, secure_permissions=False)
            self.assertEqual(item.managed_targets, [str(destination / source.name)])
            next_item = SimpleNamespace(uid='same', policy_guid='A')
            previous = dict(vars(next_item), managed_targets=item.managed_targets)
            state = GppStateManager()
            with patch.object(state, 'get_previous', return_value=[previous]):
                state.restore_file_targets(vars(next_item), next_item)
            self.assertEqual(next_item.managed_targets, item.managed_targets)
