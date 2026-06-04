#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
from unittest.mock import MagicMock, mock_open, patch

from gpoa_lib.storage.storage_writer import StorageWriter


class StorageWriterWriteTestCase(unittest.TestCase):

    @patch('gpoa_lib.storage.storage_writer.create_dconf_file_locks')
    @patch('gpoa_lib.storage.storage_writer.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_creates_ini(self, mock_file, mock_makedirs, mock_locks):
        writer = StorageWriter('testdb')
        writer.write({'Software/BaseALT/Policies/Control': {'sshd-gssapi-auth': '1'}})
        mock_makedirs.assert_called_once()
        handle = mock_file()
        written = ''.join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn('[Software/BaseALT/Policies/Control]', written)
        self.assertIn('sshd-gssapi-auth', written)
        mock_locks.assert_called_once()

    @patch('gpoa_lib.storage.storage_writer.create_dconf_file_locks')
    @patch('gpoa_lib.storage.storage_writer.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_append_mode(self, mock_file, mock_makedirs, mock_locks):
        writer = StorageWriter('testdb', append=True)
        writer.write({'Section': {'key': 'val'}})
        mock_file.assert_called_once()
        args, kwargs = mock_file.call_args
        self.assertEqual(args[1], 'a')

    @patch('gpoa_lib.storage.storage_writer.create_dconf_file_locks')
    @patch('gpoa_lib.storage.storage_writer.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_overwrite_mode(self, mock_file, mock_makedirs, mock_locks):
        writer = StorageWriter('testdb', append=False)
        writer.write({'Section': {'key': 'val'}})
        args, kwargs = mock_file.call_args
        self.assertEqual(args[1], 'w')

    @patch('gpoa_lib.storage.storage_writer.create_dconf_file_locks')
    @patch('gpoa_lib.storage.storage_writer.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_keys_groups_flat_dict(self, mock_file, mock_makedirs, mock_locks):
        writer = StorageWriter('testdb')
        writer.write_keys({'Software/BaseALT/Policies/Control/sshd': '1'})
        handle = mock_file()
        written = ''.join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn('[Software/BaseALT/Policies/Control]', written)
        self.assertIn('sshd', written)

    @patch('gpoa_lib.storage.storage_writer.create_dconf_file_locks')
    @patch('gpoa_lib.storage.storage_writer.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_write_keys_backslashes(self, mock_file, mock_makedirs, mock_locks):
        writer = StorageWriter('testdb')
        writer.write_keys({r'SOFTWARE\BaseALT\Policies\Control\sshd': '1'})
        handle = mock_file()
        written = ''.join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn('[SOFTWARE/BaseALT/Policies/Control]', written)


class StorageWriterDeleteTestCase(unittest.TestCase):

    @patch('gpoa_lib.storage.storage_writer.os.makedirs')
    @patch('builtins.open', new_callable=mock_open, read_data='[Software/BaseALT/Policies/Control]\nsshd-gssapi-auth = "1"\n\n')
    def test_delete_keys_removes_entries(self, mock_file, mock_makedirs):
        writer = StorageWriter('testdb')
        writer.delete_keys(['Software/BaseALT/Policies/Control/sshd-gssapi-auth'])
        handle = mock_file()
        write_calls = [call.args[0] for call in handle.write.call_args_list
                       if call.args[0].strip()]
        self.assertNotIn('sshd-gssapi-auth', ''.join(write_calls))

    @patch('gpoa_lib.storage.storage_writer.os.path.exists', return_value=False)
    def test_delete_keys_no_file(self, mock_exists):
        writer = StorageWriter('testdb')
        writer.delete_keys(['some/key'])
        mock_exists.assert_called_once()


class StorageWriterCompileTestCase(unittest.TestCase):

    @patch('gpoa_lib.storage.storage_writer.Dconf_registry')
    def test_compile_calls_dconf_update(self, mock_dconf):
        writer = StorageWriter('mydb', uid=1000)
        writer.compile()
        mock_dconf.dconf_update.assert_called_once_with(uid=1000, db_name='mydb')

    @patch('gpoa_lib.storage.storage_writer.Dconf_registry')
    def test_compile_no_uid(self, mock_dconf):
        writer = StorageWriter('mydb')
        writer.compile()
        mock_dconf.dconf_update.assert_called_once_with(uid=None, db_name='mydb')
