import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from gpoa_lib.frontend.chromium_applier import chromium_applier
from gpoa_lib.frontend.yandex_browser_applier import yandex_browser_applier


class BrowserJsonPolicyTest(unittest.TestCase):
    def test_managed_and_recommended_json_types_and_legacy_formats(self):
        objects = {
            'ExtensionSettings': {
                '*': {'installation_mode': 'blocked', 'override_update_url': True},
                'extension-id': {'enabled': False, 'optional': None,
                                 'path': r'C:\path\file', 'label': 'Тест',
                                 'nested': [True, {'url': 'https://example.org/a'}]},
            },
            'EmptyObject': {},
        }
        for cls in (chromium_applier, yandex_browser_applier):
            with self.subTest(browser=cls.__name__), tempfile.TemporaryDirectory() as directory:
                applier = cls.__new__(cls)
                branch = getattr(cls, f'_{cls.__name__}__registry_branch')
                for scope in ('managed', 'recommended'):
                    setattr(applier, f'_{cls.__name__}__{scope}_policies_path', str(Path(directory, scope)))
                entries = []

                def add(name, data, regtype=1):
                    entries.append(SimpleNamespace(hive_key=branch + '/' + name,
                                                   valuename=name.rsplit('/', 1)[-1],
                                                   type=regtype, data=data, keyname=name))

                expected = dict(objects)
                expected.update({
                    'LegacyObject': {'key': True},
                    'MalformedObject': '{invalid json}',
                    'ArrayPolicy': [True, False, None, {'key': 'value'}],
                    'URLBlocklist': ['example.org', 'other.example.org'],
                    'DownloadDirectory': 'C:/downloads',
                    'HomepageIsNewTabPage': True,
                    'DiskCacheSize': 102400,
                })
                for prefix in ('', 'Recommended/'):
                    for name, value in objects.items():
                        # REG_SZ may arrive as text or UTF-16 bytes.
                        text = '  ' + json.dumps(value, ensure_ascii=False) + '  '
                        add(prefix + name, text if not prefix else (text + '\0').encode('utf-16'))
                    add(prefix + 'LegacyObject', "{'key': True}")
                    add(prefix + 'MalformedObject', '{invalid json}')
                    add(prefix + 'ArrayPolicy', '[true, false, null, {"key": "value"}]')
                    add(prefix + 'URLBlocklist/1', 'example.org')
                    add(prefix + 'URLBlocklist/2', 'other.example.org')
                    add(prefix + 'DownloadDirectory', r'C:\downloads')
                    add(prefix + 'HomepageIsNewTabPage', 1, 4)
                    add(prefix + 'DiskCacheSize', 102400, 4)
                applier.create_dict(entries)
                applier.machine_apply()
                for scope in ('managed', 'recommended'):
                    output = json.loads(Path(directory, scope, 'policies.json').read_text())
                    self.assertEqual(output, expected)
                    self.assertIs(type(output['HomepageIsNewTabPage']), bool)
                    self.assertIs(type(output['DiskCacheSize']), int)
                    self.assertIs(type(output['ExtensionSettings']), dict)
