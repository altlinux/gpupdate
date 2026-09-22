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
from types import SimpleNamespace

from gpoa_lib.frontend.chromium_applier import chromium_applier


def _dword(valuename, data):
    return SimpleNamespace(
        hive_key=f'Software/Policies/Google/Chrome/{valuename}',
        valuename=valuename,
        type=4,
        data=data,
    )


class ChromiumPolicyTypeTestCase(unittest.TestCase):

    def setUp(self):
        self.applier = chromium_applier.__new__(chromium_applier)
        self.applier.policies_json = {}

    def test_integer_policies_remain_integers(self):
        self.applier.create_dict([
            _dword('DefaultIdleDetectionSetting', 2),
            _dword('DiskCacheSize', 1048576),
            _dword('ChromeFrameRendererSettings', 2),
        ])

        self.assertEqual(self.applier.policies_json, {
            'DefaultIdleDetectionSetting': 2,
            'DiskCacheSize': 1048576,
            'ChromeFrameRendererSettings': 2,
        })
        for value in self.applier.policies_json.values():
            self.assertIs(type(value), int)

    def test_regular_dword_policy_is_boolean(self):
        self.applier.create_dict([_dword('HomepageIsNewTabPage', 1)])

        self.assertIs(self.applier.policies_json['HomepageIsNewTabPage'], True)
