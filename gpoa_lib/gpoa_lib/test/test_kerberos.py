#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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
from unittest.mock import patch, MagicMock


class MachineKinitTestCase(unittest.TestCase):

    @patch('gpoa_lib.util.kerberos.check_krb_ticket', return_value=True)
    @patch('gpoa_lib.util.kerberos.get_machine_name', return_value='testhost')
    @patch('gpoa_lib.util.kerberos.smbopts')
    @patch('gpoa_lib.util.kerberos.subprocess')
    @patch('gpoa_lib.util.kerberos.log')
    def test_machine_kinit_success(self, mock_log, mock_subprocess, mock_smbopts, mock_get_name, mock_check):
        mock_opts = MagicMock()
        mock_opts.get_realm.return_value = 'TEST.REALM'
        mock_smbopts.return_value = mock_opts
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.__enter__ = MagicMock(return_value=mock_proc)
        mock_proc.__exit__ = MagicMock(return_value=False)
        mock_subprocess.Popen.return_value = mock_proc

        from gpoa_lib.util.kerberos import machine_kinit
        result = machine_kinit()

        self.assertTrue(result)

    @patch('gpoa_lib.util.kerberos.check_krb_ticket', return_value=True)
    @patch('gpoa_lib.util.kerberos.get_machine_name', return_value='testhost')
    @patch('gpoa_lib.util.kerberos.smbopts')
    @patch('gpoa_lib.util.kerberos.subprocess')
    @patch('gpoa_lib.util.kerberos.log')
    def test_machine_kinit_failure(self, mock_log, mock_subprocess, mock_smbopts, mock_get_name, mock_check):
        mock_opts = MagicMock()
        mock_opts.get_realm.return_value = 'TEST.REALM'
        mock_smbopts.return_value = mock_opts
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.__enter__ = MagicMock(return_value=mock_proc)
        mock_proc.__exit__ = MagicMock(return_value=False)
        mock_subprocess.Popen.return_value = mock_proc

        from gpoa_lib.util.kerberos import machine_kinit
        result = machine_kinit()

        self.assertFalse(result)

    @patch('gpoa_lib.util.kerberos.check_krb_ticket', return_value=True)
    @patch('gpoa_lib.util.kerberos.get_machine_name', return_value='testhost')
    @patch('gpoa_lib.util.kerberos.smbopts')
    @patch('gpoa_lib.util.kerberos.subprocess')
    @patch('gpoa_lib.util.kerberos.log')
    @patch('gpoa_lib.util.kerberos.os')
    def test_machine_kinit_with_cache_name(self, mock_os, mock_log, mock_subprocess, mock_smbopts, mock_get_name, mock_check):
        mock_os.environ = {}
        mock_opts = MagicMock()
        mock_opts.get_realm.return_value = 'TEST.REALM'
        mock_smbopts.return_value = mock_opts
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.__enter__ = MagicMock(return_value=mock_proc)
        mock_proc.__exit__ = MagicMock(return_value=False)
        mock_subprocess.Popen.return_value = mock_proc

        from gpoa_lib.util.kerberos import machine_kinit
        result = machine_kinit(cache_name='/tmp/krb5cc_test')

        self.assertTrue(result)
        self.assertEqual(mock_os.environ['KRB5CCNAME'], 'FILE:/tmp/krb5cc_test')


class MachineKdestroyTestCase(unittest.TestCase):

    @patch('gpoa_lib.util.kerberos.get_machine_name', return_value='testhost')
    @patch('gpoa_lib.util.kerberos.os')
    @patch('gpoa_lib.util.kerberos.subprocess')
    @patch('gpoa_lib.util.kerberos.log')
    def test_machine_kdestroy_with_cache_removes_file(self, mock_log, mock_subprocess, mock_os, mock_get_name):
        mock_os.path.exists.return_value = True
        mock_proc = MagicMock()
        mock_subprocess.Popen.return_value = mock_proc

        from gpoa_lib.util.kerberos import machine_kdestroy
        machine_kdestroy(cache_name='/tmp/krb5cc_test')

        mock_os.unlink.assert_called_with('/tmp/krb5cc_test')

    @patch('gpoa_lib.util.kerberos.get_machine_name', return_value='testhost')
    @patch('gpoa_lib.util.kerberos.os')
    @patch('gpoa_lib.util.kerberos.subprocess')
    @patch('gpoa_lib.util.kerberos.log')
    def test_machine_kdestroy_without_cache_uses_env(self, mock_log, mock_subprocess, mock_os, mock_get_name):
        mock_os.environ = {'KRB5CCNAME': 'FILE:/tmp/krb5cc_env'}
        mock_os.path.exists.return_value = True
        mock_proc = MagicMock()
        mock_subprocess.Popen.return_value = mock_proc

        from gpoa_lib.util.kerberos import machine_kdestroy
        machine_kdestroy()

        mock_os.unlink.assert_called_with('/tmp/krb5cc_env')


class CheckKrbTicketTestCase(unittest.TestCase):

    @patch('gpoa_lib.util.kerberos.subprocess')
    @patch('gpoa_lib.util.kerberos.log')
    def test_check_krb_ticket_present(self, mock_log, mock_subprocess):
        mock_subprocess.check_call.return_value = 0
        mock_subprocess.check_output.return_value = b'Ticket cache: FILE:/tmp/krb5cc'

        from gpoa_lib.util.kerberos import check_krb_ticket
        result = check_krb_ticket()

        self.assertTrue(result)

    @patch('gpoa_lib.util.kerberos.subprocess')
    @patch('gpoa_lib.util.kerberos.log')
    def test_check_krb_ticket_missing(self, mock_log, mock_subprocess):
        mock_subprocess.check_call.side_effect = Exception('no ticket')

        from gpoa_lib.util.kerberos import check_krb_ticket
        result = check_krb_ticket()

        self.assertFalse(result)
