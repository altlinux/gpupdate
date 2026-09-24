import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory
import smbc
import weakref
from backend.freeipa_backend import freeipa_backend


class SMBDirectory:
    """Match the public smbc.Dir API without a fictitious close() method."""
    __slots__ = ('entries', 'error', '__weakref__')

    def __init__(self, entries, error=None):
        self.entries = entries
        self.error = error

    def getdents(self):
        if self.error:
            raise self.error
        return self.entries


class SMBTree:
    def __init__(self, files, listing_error=None, transfer_error=None):
        self.files = files
        self.listing_error = listing_error
        self.transfer_error = transfer_error
        self.handles = weakref.WeakSet()
        self.opened = []

    def opendir(self, uri):
        if self.handles:
            raise AssertionError('Parent directory handle retained during recursion')
        self.opened.append(uri)
        prefix = uri + '/'
        children = {}
        for path in self.files:
            if path.startswith(prefix):
                name, separator, tail = path[len(prefix):].partition('/')
                children[name] = smbc.DIR if separator else smbc.FILE
        entries = [smbc.Dirent(name=name, comment='', smbc_type=kind)
                   for name, kind in children.items()]
        entries.extend(smbc.Dirent(name=name, comment='', smbc_type=smbc.DIR)
                       for name in ('.', '..'))
        error = OSError('SMB listing failed') if uri == self.listing_error else None
        directory = SMBDirectory(entries, error)
        self.handles.add(directory)
        return directory

    def store(self, uri, target, *, checked=False):
        if not checked:
            raise AssertionError('Snapshot transfers must be checked')
        if self.handles:
            raise AssertionError('Directory handle retained during file transfer')
        if uri == self.transfer_error:
            raise OSError('SMB transfer failed')
        Path(target).write_bytes(self.files[uri])


class FreeIPARetrievalTests(unittest.TestCase):
    def test_recursive_snapshot_uses_actual_directory_api_and_releases_handles(self):
        uri = 'smb://dc/sysvol/guid'
        files = {uri + '/GPT.INI': b'[General]\nVersion=1\n',
                 uri + '/Machine/Preferences/Files/Files.xml': b'<Files/>',
                 uri + '/Machine/payload.bin': b'\x00\xffbinary'}
        with TemporaryDirectory() as root:
            obj = self.make_backend()
            obj.ipacreds.get_cache_dir.return_value = root
            obj.ipacreds.get_domain.return_value = 'example'
            tree = SMBTree(files)
            obj.file_cache = SimpleNamespace(samba_context=tree, store=tree.store)
            policy = SimpleNamespace(name='guid', display_name='policy',
                                     file_sys_path='\\\\dc\\sysvol\\guid')
            obj._download_gpos([policy], 'dc')
            snapshot = Path(policy.file_sys_path)
            self.assertEqual({path.relative_to(snapshot).as_posix(): path.read_bytes()
                              for path in snapshot.rglob('*') if path.is_file()},
                             {path[len(uri) + 1:]: value for path, value in files.items()})
            self.assertEqual([uri, uri + '/Machine', uri + '/Machine/Preferences',
                              uri + '/Machine/Preferences/Files'], tree.opened)
            self.assertFalse(tree.handles)

    def test_directory_and_transfer_errors_preserve_old_snapshot(self):
        uri = 'smb://dc/sysvol/guid'
        files = {uri + '/GPT.INI': b'[General]\nVersion=1\n',
                 uri + '/Machine/payload.bin': b'new'}
        for failure in ('listing', 'transfer'):
            with self.subTest(failure=failure), TemporaryDirectory() as root:
                obj = self.make_backend()
                obj.ipacreds.get_cache_dir.return_value = root
                obj.ipacreds.get_domain.return_value = 'example'
                old = Path(root, 'EXAMPLE', 'POLICIES', 'guid')
                old.mkdir(parents=True)
                (old / 'sentinel').write_bytes(b'old')
                tree = SMBTree(files,
                               listing_error=uri + '/Machine' if failure == 'listing' else None,
                               transfer_error=uri + '/Machine/payload.bin' if failure == 'transfer' else None)
                obj.file_cache = SimpleNamespace(samba_context=tree, store=tree.store)
                policy = SimpleNamespace(name='guid', display_name='policy',
                                         file_sys_path='\\\\dc\\sysvol\\guid')
                with self.assertRaisesRegex(OSError, 'SMB ' + failure + ' failed'):
                    obj._download_gpos([policy], 'dc')
                self.assertEqual('\\\\dc\\sysvol\\guid', policy.file_sys_path)
                self.assertEqual(b'old', (old / 'sentinel').read_bytes())
                self.assertEqual([old], list(old.parent.iterdir()))

    def test_snapshots_preserve_old_content_and_retry_failed_download(self):
        with TemporaryDirectory() as root:
            obj = self.make_backend()
            obj.ipacreds.get_cache_dir.return_value = root
            obj.ipacreds.get_domain.return_value = 'example'
            old = Path(root, 'EXAMPLE', 'POLICIES', 'guid')
            old.mkdir(parents=True)
            (old / 'obsolete').write_text('keep until successful refresh')
            policy = SimpleNamespace(name='guid', display_name='policy', file_sys_path='\\\\dc\\sysvol\\guid')
            def download(remote, target):
                Path(target).mkdir()
                Path(target, 'current.txt').write_text('new')
            obj._download_gpo_directory = Mock(side_effect=RuntimeError('partial'))
            with self.assertRaises(RuntimeError):
                obj._download_gpos([policy], 'dc')
            self.assertEqual(policy.file_sys_path, '\\\\dc\\sysvol\\guid')
            self.assertEqual(list(old.parent.iterdir()), [old])
            obj._download_gpo_directory.side_effect = download
            obj._download_gpos([policy], 'dc')
            snapshot = Path(policy.file_sys_path)
            self.assertEqual(snapshot.name, 'guid')
            self.assertTrue((snapshot / 'current.txt').exists())
            self.assertFalse((snapshot / 'obsolete').exists())
            self.assertTrue((old / 'obsolete').exists())

    def test_invalid_snapshot_is_not_published(self):
        with TemporaryDirectory() as root:
            obj = self.make_backend()
            obj.ipacreds.get_cache_dir.return_value = root
            obj.ipacreds.get_domain.return_value = 'example'
            policy = SimpleNamespace(name='guid', display_name='policy', file_sys_path='\\\\dc\\sysvol\\guid')
            def download(remote, target):
                Path(target).mkdir()
                Path(target, 'Files.xml').write_text('<broken')
            obj._download_gpo_directory = download
            with self.assertRaises(Exception):
                obj._download_gpos([policy], 'dc')
            self.assertTrue(policy.file_sys_path.startswith('\\\\'))
            self.assertEqual(list(Path(root, 'EXAMPLE', 'POLICIES').iterdir()), [])

    def make_backend(self, machine=True):
        obj = freeipa_backend.__new__(freeipa_backend)
        obj._freeipa_backend__kinit_successful = False
        obj._is_machine_username = machine
        obj.username = 'user'
        obj.storage = Mock()
        obj.ipacreds = Mock()
        return obj

    def test_chain_failure_propagates_before_application(self):
        for machine in (True, False):
            obj = self.make_backend(machine)
            obj.ipacreds.update_gpos.side_effect = RuntimeError('offline')
            with patch('backend.freeipa_backend.Dconf_registry'), patch('backend.freeipa_backend.get_uid_by_username'), \
                    patch('backend.freeipa_backend.get_local_gpt') as local:
                with self.assertRaisesRegex(RuntimeError, 'offline'):
                    obj.retrieve_and_store()
                local.assert_not_called()

    def test_successful_empty_chain_still_uses_local_policy(self):
        obj = self.make_backend()
        obj.ipacreds.update_gpos.return_value = ([], 'ipa.example')
        with patch('backend.freeipa_backend.get_local_gpt', return_value='local'):
            self.assertEqual(obj._get_gpts('host'), ['local'])

    def test_mixed_cache_states_preserve_chain_order(self):
        for cached in ((), ('A',), ('B',), ('A', 'B')):
            obj = self.make_backend()
            chain = [SimpleNamespace(name=n, display_name=n, file_sys_path='/' + n if n in cached else '\\\\dc\\' + n) for n in ('A', 'B')]
            obj.ipacreds.update_gpos.return_value = (chain, 'ipa.example')
            def download(gpos, server):
                for policy in gpos:
                    policy.file_sys_path = '/' + policy.name
            obj._download_gpos = download
            with patch('backend.freeipa_backend.os.path.exists', return_value=True), \
                    patch('backend.freeipa_backend.GpoInfoDconf'), \
                    patch('backend.freeipa_backend.get_local_gpt', return_value='local'), \
                    patch('backend.freeipa_backend.gpt', side_effect=lambda path, *a: Mock(path=path)):
                result = obj._get_gpts('host')
                self.assertEqual([p.path for p in result[:-1]], ['/A', '/B'])
                self.assertEqual(result[-1], 'local')
