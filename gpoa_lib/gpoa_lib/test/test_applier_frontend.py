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
from unittest.mock import MagicMock

from gpoa_lib.frontend.applier_frontend import (
    check_experimental_enabled,
    check_windows_mapping_enabled,
    check_module_enabled,
    check_enabled,
    DualContextApplier,
)


class CheckExperimentalEnabledTestCase(unittest.TestCase):

    def test_returns_true_when_flag_is_1(self):
        storage = MagicMock()
        storage.get_key_value.return_value = '1'
        self.assertTrue(check_experimental_enabled(storage))

    def test_returns_false_when_flag_is_0(self):
        storage = MagicMock()
        storage.get_key_value.return_value = '0'
        self.assertFalse(check_experimental_enabled(storage))

    def test_returns_false_when_flag_is_none(self):
        storage = MagicMock()
        storage.get_key_value.return_value = None
        self.assertFalse(check_experimental_enabled(storage))


class CheckWindowsMappingEnabledTestCase(unittest.TestCase):

    def test_default_true_when_none(self):
        storage = MagicMock()
        storage.get_key_value.return_value = None
        self.assertTrue(check_windows_mapping_enabled(storage))

    def test_returns_false_when_flag_is_0(self):
        storage = MagicMock()
        storage.get_key_value.return_value = '0'
        self.assertFalse(check_windows_mapping_enabled(storage))

    def test_returns_true_when_flag_is_1(self):
        storage = MagicMock()
        storage.get_key_value.return_value = '1'
        self.assertTrue(check_windows_mapping_enabled(storage))


class CheckModuleEnabledTestCase(unittest.TestCase):

    def test_returns_true_when_flag_is_1(self):
        storage = MagicMock()
        storage.get_key_value.return_value = '1'
        self.assertTrue(check_module_enabled(storage, 'TestModule'))

    def test_returns_false_when_flag_is_0(self):
        storage = MagicMock()
        storage.get_key_value.return_value = '0'
        self.assertFalse(check_module_enabled(storage, 'TestModule'))

    def test_returns_none_when_flag_is_none(self):
        storage = MagicMock()
        storage.get_key_value.return_value = None
        self.assertIsNone(check_module_enabled(storage, 'TestModule'))


class CheckEnabledTestCase(unittest.TestCase):

    def test_non_experimental_enabled_by_default(self):
        storage = MagicMock()
        storage.get_key_value.return_value = None
        self.assertTrue(check_enabled(storage, 'TestModule', False))

    def test_experimental_enabled_when_global_on(self):
        storage = MagicMock()
        storage.get_key_value.side_effect = [None, '1']
        self.assertTrue(check_enabled(storage, 'TestModule', True))

    def test_experimental_disabled_when_global_off(self):
        storage = MagicMock()
        storage.get_key_value.side_effect = [None, '0']
        self.assertFalse(check_enabled(storage, 'TestModule', True))

    def test_module_enabled_overrides_experimental(self):
        storage = MagicMock()
        storage.get_key_value.side_effect = ['1', '0']
        self.assertTrue(check_enabled(storage, 'TestModule', True))


class DualContextApplierTestCase(unittest.TestCase):

    def test_apply_calls_admin_context_apply(self):
        applier = DualContextApplier(MagicMock())
        applier.admin_context_apply = MagicMock()
        applier.apply()
        applier.admin_context_apply.assert_called_once()
