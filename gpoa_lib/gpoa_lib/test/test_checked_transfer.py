import tempfile
import unittest
import smbc
import weakref
from pathlib import Path
from unittest.mock import Mock, patch
from gpoa_lib.storage.fs_file_cache import fs_file_cache


class CheckedTransferTest(unittest.TestCase):
    def test_smb_listing_requires_only_getdents_and_preserves_error_contract(self):
        class Directory:
            __slots__ = ('__weakref__',)

            def getdents(self):
                return [smbc.Dirent(name=name, comment='', smbc_type=kind)
                        for name, kind in (('file.pub', smbc.FILE), ('folder', smbc.DIR))]

        references = []
        def opendir(uri):
            directory = Directory()
            references.append(weakref.ref(directory))
            return directory

        cache = fs_file_cache.__new__(fs_file_cache)
        cache.samba_context = Mock()
        cache.samba_context.opendir.side_effect = opendir
        self.assertEqual(['file.pub'], cache.get_ls_smbdir('smb://server/share', checked=True))
        self.assertIsNone(references[0]())
        cache.samba_context.opendir.side_effect = OSError('offline')
        with self.assertRaisesRegex(OSError, 'offline'):
            cache.get_ls_smbdir('smb://server/share', checked=True)
        self.assertIsNone(cache.get_ls_smbdir('smb://server/share'))

    def test_partial_read_preserves_old_file_and_reports_error(self):
        cache = fs_file_cache.__new__(fs_file_cache)
        cache.samba_context = Mock()
        cache.samba_context.open.return_value.read.side_effect = [b'partial', OSError('read failed')]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'file'
            target.write_text('old')
            with self.assertRaises(OSError):
                cache.store('smb://server/share/file', target, checked=True)
            self.assertEqual(target.read_text(), 'old')
            self.assertEqual(list(Path(tmp).iterdir()), [target])
            cache.samba_context.open.side_effect = OSError('offline')
            self.assertIsNone(cache.store('smb://server/share/file', target))
            with patch('gpoa_lib.storage.fs_file_cache.tempfile.mkstemp', side_effect=OSError('full')):
                with self.assertRaisesRegex(OSError, 'full'):
                    cache.store('smb://server/share/file', target, checked=True)
