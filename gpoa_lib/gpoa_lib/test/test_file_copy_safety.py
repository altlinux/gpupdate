from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gpoa_lib.frontend.appliers.file_cp import Files_cp


class FileCopySafetyTests(unittest.TestCase):
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
