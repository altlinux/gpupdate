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

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from gpoa_lib.frontend.yandex_browser_applier import yandex_browser_applier
from gpoa_lib.storage.dconf_registry import Dconf_registry, load_preg_dconf


class YandexIntegerPoliciesTest(unittest.TestCase):
    NUMERIC_VALUES = {
        'YandexLoginAllowedDomainsForceLogoutMaxDelay': (0, 1, 1440),
        'BrowserSwitcherDelay': (0, 1, 300),
        'PolicyRefreshRate': (1800000, 5000000, 86400000),
        'CloudReportingUploadFrequency': (3, 4, 24),
        'YandexClipboardMaxImageSize': (0, 1, 5242880),
        'YandexClipboardMaxTextSize': (0, 1, 1000),
        'MaxConnectionsPerProxy': (6, 7, 100),
        'IntranetRedirectBehavior': (0, 1, 3),
        'ImportFrom': (0, 1, 4),
    }

    def test_registry_dwords_remain_numbers_in_both_outputs(self):
        state = patch.multiple(Dconf_registry, global_registry_dict={},
                               _dconf_db={}, _gpt_read_flag=True)
        with state, tempfile.TemporaryDirectory() as directory:
            branch = yandex_browser_applier._yandex_browser_applier__registry_branch
            root = Path(directory)
            applier = yandex_browser_applier.__new__(yandex_browser_applier)
            for scope in ('managed', 'recommended'):
                setattr(applier, '_yandex_browser_applier__' + scope + '_policies_path',
                        str(root / scope))
            for position in range(3):
                expected = {name: values[position]
                            for name, values in self.NUMERIC_VALUES.items()}
                expected.update({'DiskCacheSize': 1048576,
                                 'DownloadRestrictions': 0,
                                 'VideoCaptureAllowed': True,
                                 'AudioCaptureAllowed': False})
                entries = []
                for suffix in ('', '/Recommended'):
                    for name, value in expected.items():
                        entries.append(SimpleNamespace(
                            keyname=(branch + suffix).replace('/', '\\'),
                            valuename=name, data=int(value), type=4))
                Dconf_registry.global_registry_dict = {}
                load_preg_dconf(SimpleNamespace(entries=entries), 'fixture.pol',
                                'Yandex numeric policies', None, None)
                applier.create_dict(Dconf_registry.filter_hklm_entries(branch))
                applier.machine_apply()
                for scope in ('managed', 'recommended'):
                    with self.subTest(position=position, scope=scope):
                        output = json.loads((root / scope / 'policies.json').read_text())
                        self.assertEqual(expected, output)
                        for name in (*self.NUMERIC_VALUES, 'DiskCacheSize',
                                     'DownloadRestrictions'):
                            self.assertIs(type(output[name]), int, name)
                        for name in ('VideoCaptureAllowed', 'AudioCaptureAllowed'):
                            self.assertIs(type(output[name]), bool, name)

    def test_existing_exceptions_are_retained_without_duplicates(self):
        applier = yandex_browser_applier.__new__(yandex_browser_applier)
        names = applier.get_valuename_typeint()
        self.assertEqual(len(names), len(set(names)))
        for name in ('RestoreOnStartup_recommended', 'DefaultPluginsSetting',
                     'DiskCacheSize', 'DefaultUploadSetting'):
            self.assertIn(name, names)
