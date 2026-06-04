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

from gpoa_lib.applier_runner import ApplierRunner, _get_applier_map, _join_prefix
from gpoa_lib.result import Result


class ApplierRunnerHelpersTestCase(unittest.TestCase):

    def test_join_prefix(self):
        result = _join_prefix('Software/MyOrg/Policies', 'control')
        self.assertEqual(result, 'Software/MyOrg/Policies/control')

    def test_join_prefix_trailing_slash(self):
        result = _join_prefix('Software/MyOrg/Policies/', 'control')
        self.assertEqual(result, 'Software/MyOrg/Policies/control')

    def test_join_prefix_backslashes(self):
        result = _join_prefix(r'Software\MyOrg\Policies', 'control')
        self.assertEqual(result, 'Software/MyOrg/Policies/control')


class ApplierRunnerMapTestCase(unittest.TestCase):

    def test_applier_map_has_expected_entries(self):
        amap = _get_applier_map()
        expected = [
            'control', 'chromium', 'firefox', 'thunderbird', 'yandex_browser',
            'firewall', 'gsettings', 'kde', 'ntp', 'package', 'polkit', 'systemd',
        ]
        for name in expected:
            self.assertIn(name, amap, f'{name} not in APPLIER_MAP')

    def test_each_entry_has_class_and_branch(self):
        amap = _get_applier_map()
        for name, entry in amap.items():
            self.assertIn('class', entry, f'{name} missing class')
            self.assertIn('branch', entry, f'{name} missing branch')
            self.assertTrue(callable(entry['class']), f'{name} class not callable')

    def test_list_appliers(self):
        names = ApplierRunner.list_appliers()
        self.assertIsInstance(names, list)
        self.assertGreater(len(names), 0)
        self.assertIn('control', names)


class ApplierRunnerCreateTestCase(unittest.TestCase):

    def test_create_control_from_dict(self):
        data = {
            'Software/BaseALT/Policies/Control': {
                'sshd-gssapi-auth': '1',
            }
        }
        runner = ApplierRunner(data=data)
        result = runner.create('control')
        self.assertTrue(result)
        self.assertIsNotNone(result.data)

    def test_create_with_custom_prefix(self):
        data = {
            'Software/MyOrg/Policies/Control': {
                'sshd-gssapi-auth': '1',
            }
        }
        runner = ApplierRunner(data=data)
        result = runner.create('control', prefix='Software/MyOrg/Policies')
        self.assertTrue(result)

    def test_create_with_keys(self):
        data = {
            'Software/BaseALT/Policies/Control': {
                'sshd-gssapi-auth': '1',
            }
        }
        runner = ApplierRunner(data=data)
        result = runner.create('control', keys=[
            'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
        ])
        self.assertTrue(result)

    def test_create_unknown_applier(self):
        runner = ApplierRunner(data={})
        result = runner.create('nonexistent')
        self.assertFalse(result)
        self.assertIsNotNone(result.error)

    def test_create_systemd_from_dict(self):
        data = {
            'Software/BaseALT/Policies/SystemdUnits': {
                'sshd.service': '1',
            }
        }
        runner = ApplierRunner(data=data)
        result = runner.create('systemd')
        self.assertTrue(result)


class ApplierRunnerResolveTestCase(unittest.TestCase):

    def test_resolve_control(self):
        name = ApplierRunner.resolve('Software/BaseALT/Policies/Control/sshd-gssapi-auth')
        self.assertEqual(name, 'control')

    def test_resolve_firefox(self):
        name = ApplierRunner.resolve('Software/Policies/Mozilla/Firefox')
        self.assertEqual(name, 'firefox')

    def test_resolve_kde(self):
        name = ApplierRunner.resolve('Software/BaseALT/Policies/KDE')
        self.assertEqual(name, 'kde')

    def test_resolve_unknown(self):
        name = ApplierRunner.resolve('Software/Unknown/Path')
        self.assertIsNone(name)

    def test_resolve_backslashes(self):
        name = ApplierRunner.resolve(r'SOFTWARE\BaseALT\Policies\Control\test')
        self.assertEqual(name, 'control')

    def test_resolve_case_insensitive(self):
        name = ApplierRunner.resolve('software/basealt/policies/control/test')
        self.assertEqual(name, 'control')


class ApplierRunnerForceTestCase(unittest.TestCase):

    def test_force_default_false(self):
        runner = ApplierRunner(data={})
        self.assertFalse(runner.force)

    def test_force_true(self):
        runner = ApplierRunner(data={}, force=True)
        self.assertTrue(runner.force)


class ResultTestCase(unittest.TestCase):

    def test_ok_result(self):
        r = Result.ok(42)
        self.assertTrue(r)
        self.assertEqual(r.data, 42)
        self.assertIsNone(r.error)

    def test_ok_result_no_data(self):
        r = Result.ok()
        self.assertTrue(r)
        self.assertIsNone(r.data)

    def test_fail_result(self):
        r = Result.fail('something went wrong')
        self.assertFalse(r)
        self.assertEqual(r.error, 'something went wrong')
        self.assertIsNone(r.data)

    def test_result_repr_ok(self):
        r = Result.ok(42)
        self.assertIn('ok=True', repr(r))

    def test_result_repr_fail(self):
        r = Result.fail('err')
        self.assertIn('ok=False', repr(r))
