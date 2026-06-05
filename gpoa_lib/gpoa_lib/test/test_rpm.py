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


class IsRpmInstalledTestCase(unittest.TestCase):

    @patch('gpoa_lib.util.rpm.rpm')
    def test_rpm_installed_true(self, mock_rpm):
        mock_ts = MagicMock()
        mock_rpm.TransactionSet.return_value = mock_ts
        mock_pm = MagicMock()
        mock_pm.count.return_value = 1
        mock_ts.dbMatch.return_value = mock_pm

        from gpoa_lib.util.rpm import is_rpm_installed
        self.assertTrue(is_rpm_installed('test-pkg'))

    @patch('gpoa_lib.util.rpm.rpm')
    def test_rpm_installed_false(self, mock_rpm):
        mock_ts = MagicMock()
        mock_rpm.TransactionSet.return_value = mock_ts
        mock_pm = MagicMock()
        mock_pm.count.return_value = 0
        mock_ts.dbMatch.return_value = mock_pm

        from gpoa_lib.util.rpm import is_rpm_installed
        self.assertFalse(is_rpm_installed('test-pkg'))


class PackageInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=False)
    def test_package_name_with_dash_suffix(self, mock_installed):
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg-')
        self.assertEqual(pkg.package_name, 'test-pkg')
        self.assertFalse(pkg.for_install)

    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=False)
    def test_package_name_without_dash(self, mock_installed):
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg')
        self.assertEqual(pkg.package_name, 'test-pkg')
        self.assertTrue(pkg.for_install)


class PackageMarkTestCase(unittest.TestCase):

    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=False)
    def test_mark_for_install(self, mock_installed):
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg-')
        self.assertFalse(pkg.for_install)
        pkg.mark_for_install()
        self.assertTrue(pkg.for_install)

    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=True)
    def test_mark_for_removal(self, mock_installed):
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg')
        self.assertTrue(pkg.for_install)
        pkg.mark_for_removal()
        self.assertFalse(pkg.for_install)


class PackageActionTestCase(unittest.TestCase):

    @patch('gpoa_lib.util.rpm.subprocess')
    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=False)
    def test_action_install_when_not_installed(self, mock_installed, mock_subprocess):
        mock_subprocess.check_call.return_value = 0
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg')
        pkg.action()
        mock_subprocess.check_call.assert_called_once_with(
            ['/usr/bin/apt-get', '-y', 'install', 'test-pkg'], timeout=120
        )

    @patch('gpoa_lib.util.rpm.subprocess')
    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=True)
    def test_action_install_skip_when_installed(self, mock_installed, mock_subprocess):
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg')
        pkg.action()
        mock_subprocess.check_call.assert_not_called()

    @patch('gpoa_lib.util.rpm.subprocess')
    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=True)
    def test_action_remove_when_installed(self, mock_installed, mock_subprocess):
        mock_subprocess.check_call.return_value = 0
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg-')
        pkg.action()
        mock_subprocess.check_call.assert_called_once_with(
            ['/usr/bin/apt-get', '-y', 'remove', 'test-pkg'], timeout=120
        )

    @patch('gpoa_lib.util.rpm.subprocess')
    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=False)
    def test_action_remove_skip_when_not_installed(self, mock_installed, mock_subprocess):
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg-')
        pkg.action()
        mock_subprocess.check_call.assert_not_called()


class PackageMutabilityTestCase(unittest.TestCase):

    @patch('gpoa_lib.util.rpm.subprocess')
    @patch('gpoa_lib.util.rpm.is_rpm_installed', return_value=False)
    def test_install_does_not_mutate_command_list(self, mock_installed, mock_subprocess):
        mock_subprocess.check_call.return_value = 0
        from gpoa_lib.util.rpm import Package
        pkg = Package('test-pkg')
        pkg.install()
        pkg.install()
        calls = mock_subprocess.check_call.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
