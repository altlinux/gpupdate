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

from gpoa_lib.frontend.appliers.netshare import Networkshare
from gpoa_lib.util.arguments import FileAction


def _make_share_obj(action='C', name='myshare', path='/data/share',
                    allRegular=False, comment='test share',
                    limitUsers=False, abe=False):
    obj = MagicMock()
    obj.name = name
    obj.path = path
    obj.action = action
    obj.allRegular = allRegular
    obj.comment = comment
    obj.limitUsers = limitUsers
    obj.abe = abe
    return obj


class NetworkshareInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.netshare.subprocess.check_output', return_value='')
    @patch('gpoa_lib.frontend.appliers.netshare.expand_windows_var', side_effect=lambda p, u: p)
    def test_constructor_extracts_name(self, mock_expand, mock_check):
        obj = _make_share_obj(name='testshare')
        ns = Networkshare(obj)
        self.assertEqual(ns.name, 'testshare')


class NetworkshareActionTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.netshare.subprocess.check_output', return_value='')
    @patch('gpoa_lib.frontend.appliers.netshare.expand_windows_var', side_effect=lambda p, u: p)
    def test_create_action_command(self, mock_expand, mock_check):
        obj = _make_share_obj(action='C')
        ns = Networkshare(obj)
        self.assertIn('add', ns.net_full_cmd)
        self.assertIn('myshare', ns.net_full_cmd)

    @patch('gpoa_lib.frontend.appliers.netshare.subprocess.check_output', return_value='')
    @patch('gpoa_lib.frontend.appliers.netshare.expand_windows_var', side_effect=lambda p, u: p)
    def test_delete_action_command(self, mock_expand, mock_check):
        obj = _make_share_obj(action='D')
        ns = Networkshare(obj)
        self.assertIn('delete', ns.net_full_cmd)
        self.assertIn('myshare', ns.net_full_cmd)

    @patch('gpoa_lib.frontend.appliers.netshare.subprocess.check_output', return_value='')
    @patch('gpoa_lib.frontend.appliers.netshare.expand_windows_var', side_effect=lambda p, u: p)
    def test_update_action_uses_create(self, mock_expand, mock_check):
        obj = _make_share_obj(action='U')
        ns = Networkshare(obj)
        self.assertIn('add', ns.net_full_cmd)

    @patch('gpoa_lib.frontend.appliers.netshare.subprocess.check_output', return_value='')
    @patch('gpoa_lib.frontend.appliers.netshare.expand_windows_var', side_effect=lambda p, u: p)
    def test_replace_action_uses_create(self, mock_expand, mock_check):
        obj = _make_share_obj(action='R')
        ns = Networkshare(obj)
        self.assertIn('add', ns.net_full_cmd)


class NetworkshareCheckListTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.netshare.subprocess.check_output')
    @patch('gpoa_lib.frontend.appliers.netshare.expand_windows_var', side_effect=lambda p, u: p)
    def test_check_list_net_success(self, mock_expand, mock_check):
        mock_check.return_value = 'share1\nshare2\n'
        obj = _make_share_obj(action='D')
        ns = Networkshare(obj)
        mock_check.reset_mock()
        result = ns.check_list_net()
        self.assertIn('share1', result)

    @patch('gpoa_lib.frontend.appliers.netshare.subprocess.check_output')
    @patch('gpoa_lib.frontend.appliers.netshare.expand_windows_var', side_effect=lambda p, u: p)
    def test_check_list_net_failure(self, mock_expand, mock_check):
        mock_check.side_effect = Exception('cmd failed')
        obj = _make_share_obj(action='D')
        ns = Networkshare(obj)
        mock_check.reset_mock()
        mock_check.side_effect = Exception('cmd failed')
        result = ns.check_list_net()
        self.assertIsInstance(result, Exception)
