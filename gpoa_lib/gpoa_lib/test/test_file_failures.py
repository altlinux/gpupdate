import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from gpoa_lib.frontend.appliers.file_cp import Files_cp


def preference(source, target, action='C'):
    return SimpleNamespace(fromPath=str(source), targetPath=str(target), action=action,
                           readOnly=False, archive=False, hidden=False, suppress=False, executable=False)


class FileFailuresTest(unittest.TestCase):
    def test_missing_source_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            for action in ('C', 'U'):
                with self.assertRaises(FileNotFoundError):
                    Files_cp(preference(Path(tmp) / 'missing', target, action), Mock(), Mock())
            self.assertFalse(target.exists())

    def test_checked_smb_failure_is_reported(self):
        cache = Mock()
        cache.store.side_effect = OSError('offline')
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(OSError):
                Files_cp(preference('smb://server/share/file', Path(tmp) / 'file'), cache, Mock())
            self.assertTrue(cache.store.call_args.kwargs['checked'])
