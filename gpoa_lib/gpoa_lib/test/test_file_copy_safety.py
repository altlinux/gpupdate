from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gpoa_lib.frontend.appliers.file_cp import Files_cp


class FileCopySafetyTests(unittest.TestCase):
    def test_update_keeps_external_directory_ownership(self):
        with TemporaryDirectory() as directory:
            item = Files_cp.__new__(Files_cp)
            item.targetPath = Path(directory)
            item.fromPath = '/source/file'
            item.fromPathFiles = [item.fromPath]
            item.username = 'alice'
            item.file_obj = SimpleNamespace()
            item.managed_targets = []
            item.pw = SimpleNamespace(pw_gid=1000)
            item.get_target_file = Mock(return_value=item.targetPath / 'file')
            item.copy_target_file = Mock()
            item.set_mod_file = Mock()
            with patch('gpoa_lib.frontend.appliers.file_cp.shutil.chown') as chown, \
                    patch('gpoa_lib.frontend.appliers.file_cp.grp.getgrgid',
                          return_value=SimpleNamespace(gr_name='domain users')), \
                    patch('gpoa_lib.frontend.appliers.file_cp.get_homedir', return_value='/home/alice'):
                item._update_action()
            item.copy_target_file.assert_called_once()
            item.set_mod_file.assert_called_once()
            chown.assert_not_called()

    def test_local_patterns_do_not_copy_unmatched_files(self):
        with TemporaryDirectory() as directory:
            source = Path(directory)
            for name in ('host.pub', 'host.private', 'a.pub'):
                (source / name).touch()
            (source / 'directory.pub').mkdir()
            for pattern, expected in (('*.pub', {'host.pub', 'a.pub'}),
                                      ('?.pub', {'a.pub'}), ('*.none', set())):
                item = Files_cp.__new__(Files_cp)
                item.fromPath = str(source / pattern)
                item.targetPath = source / 'output'
                item.fromPathFiles = []
                item.get_list_files()
                self.assertEqual({Path(p).name for p in item.fromPathFiles}, expected)
