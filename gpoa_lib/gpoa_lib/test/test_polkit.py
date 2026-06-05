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
import unittest
from unittest.mock import patch, mock_open, MagicMock

from gpoa_lib.frontend.appliers.polkit import polkit


class PolkitOutfileTestCase(unittest.TestCase):

    def test_outfile_with_username(self):
        p = polkit('myrule', {'User': 'testuser'}, username='testuser')
        expected = os.path.join('/etc/polkit-1/rules.d', 'myrule.testuser.rules')
        self.assertEqual(p.outfile, expected)

    def test_outfile_without_username(self):
        p = polkit('myrule', {'User': 'testuser'})
        expected = os.path.join('/etc/polkit-1/rules.d', 'myrule.rules')
        self.assertEqual(p.outfile, expected)


class PolkitIsEmptyTestCase(unittest.TestCase):

    def test_all_empty(self):
        p = polkit('myrule', {'User': 'u', 'key1': '', 'key2': None})
        self.assertTrue(p._is_empty())

    def test_has_values(self):
        p = polkit('myrule', {'User': 'u', 'key1': '', 'key2': 'value'})
        self.assertFalse(p._is_empty())


class PolkitGenerateTestCase(unittest.TestCase):

    @patch('builtins.open', mock_open())
    @patch('gpoa_lib.frontend.appliers.polkit.jinja2.Environment')
    def test_generate_creates_file(self, mock_env_cls):
        mock_template = MagicMock()
        mock_template.render.return_value = 'rendered content'
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template
        mock_env_cls.return_value = mock_env

        p = polkit('myrule', {'User': 'u', 'action': 'allow'})
        p.__class__._polkit__template_environment = mock_env
        p.generate()

        mock_env.get_template.assert_called_once()
        mock_template.render.assert_called_once()

    @patch('os.path.isfile', return_value=True)
    @patch('os.remove')
    def test_generate_removes_file_when_empty(self, mock_remove, mock_isfile):
        p = polkit('myrule', {'User': 'u', 'key1': ''})
        p.generate()
        mock_remove.assert_called_once_with(p.outfile)


class PolkitErrorTestCase(unittest.TestCase):

    @patch('builtins.open', mock_open())
    @patch('gpoa_lib.frontend.appliers.polkit.jinja2.Environment')
    def test_generate_handles_template_exception(self, mock_env_cls):
        mock_env = MagicMock()
        mock_env.get_template.side_effect = Exception('template error')
        mock_env_cls.return_value = mock_env

        p = polkit('myrule', {'User': 'u', 'action': 'allow'})
        p.__class__._polkit__template_environment = mock_env
        p.generate()

        mock_env.get_template.assert_called_once()
