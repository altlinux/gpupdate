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

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from gpoa_lib.frontend.appliers.folder import Folder, str2bool


def _make_folder_obj(action='C', path='/tmp/testfolder',
                     delete_files='false', delete_folder='false',
                     delete_sub_folders='false', hidden_folder='false'):
    obj = MagicMock()
    obj.action = action
    obj.path = path
    obj.delete_files = delete_files
    obj.delete_folder = delete_folder
    obj.delete_sub_folders = delete_sub_folders
    obj.hidden_folder = hidden_folder
    return obj


class Str2BoolTestCase(unittest.TestCase):

    def test_true_strings(self):
        for val in ('true', 'yes', '1'):
            with self.subTest(val=val):
                self.assertTrue(str2bool(val))

    def test_false_strings(self):
        for val in ('false', 'no', '0'):
            with self.subTest(val=val):
                self.assertFalse(str2bool(val))

    def test_bool_true(self):
        self.assertTrue(str2bool(True))

    def test_bool_false(self):
        self.assertFalse(str2bool(False))

    def test_int_one(self):
        self.assertTrue(str2bool(1))

    def test_int_zero(self):
        self.assertFalse(str2bool(0))


class FolderActTestCase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch('gpoa_lib.frontend.appliers.folder.expand_windows_var', side_effect=lambda v, u: v)
    def test_create_action(self, mock_expand):
        folder_path = os.path.join(self.tmpdir, 'newfolder')
        folder_obj = _make_folder_obj(action='C', path=folder_path)
        folder = Folder(folder_obj, username=None)
        folder.act()
        self.assertTrue(Path(folder_path).exists())
        self.assertTrue(Path(folder_path).is_dir())

    @patch('gpoa_lib.frontend.appliers.folder.remove_dir_tree')
    @patch('gpoa_lib.frontend.appliers.folder.expand_windows_var', side_effect=lambda v, u: v)
    def test_delete_action(self, mock_expand, mock_remove):
        folder_path = os.path.join(self.tmpdir, 'delfolder')
        os.makedirs(folder_path)
        folder_obj = _make_folder_obj(action='D', path=folder_path)
        folder = Folder(folder_obj, username=None)
        folder.act()
        mock_remove.assert_called_once()

    @patch('gpoa_lib.frontend.appliers.folder.remove_dir_tree')
    @patch('gpoa_lib.frontend.appliers.folder.expand_windows_var', side_effect=lambda v, u: v)
    def test_replace_action(self, mock_expand, mock_remove):
        folder_path = os.path.join(self.tmpdir, 'replacefolder')
        os.makedirs(folder_path)
        folder_obj = _make_folder_obj(action='R', path=folder_path)
        folder = Folder(folder_obj, username=None)
        folder.act()
        mock_remove.assert_called_once()
        self.assertTrue(Path(folder_path).exists())

    @patch('gpoa_lib.frontend.appliers.folder.expand_windows_var', side_effect=lambda v, u: v)
    def test_hidden_folder_dot_prefix(self, mock_expand):
        folder_path = os.path.join(self.tmpdir, 'myfolder')
        folder_obj = _make_folder_obj(action='C', path=folder_path, hidden_folder='true')
        folder = Folder(folder_obj, username=None)
        folder.act()
        hidden_path = os.path.join(self.tmpdir, '.myfolder')
        self.assertTrue(Path(hidden_path).exists())
        self.assertFalse(Path(folder_path).exists())

    @patch('gpoa_lib.frontend.appliers.folder.expand_windows_var', side_effect=lambda v, u: v)
    def test_hidden_folder_already_dotted(self, mock_expand):
        folder_path = os.path.join(self.tmpdir, '.hidden')
        folder_obj = _make_folder_obj(action='C', path=folder_path, hidden_folder='true')
        folder = Folder(folder_obj, username=None)
        folder.act()
        self.assertTrue(Path(folder_path).exists())
