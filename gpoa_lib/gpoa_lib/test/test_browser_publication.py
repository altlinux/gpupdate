import importlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from gpoa_lib.util.atomic_files import publish_files


class BrowserPublicationTest(TestCase):
    def test_both_payloads_are_prepared_before_any_live_write(self):
        for name in ('chromium_applier', 'yandex_browser_applier'):
            module = importlib.import_module('gpoa_lib.frontend.' + name)
            cls = getattr(module, name)
            with TemporaryDirectory() as directory:
                paths = [Path(directory, part, 'policies.json') for part in ('managed', 'recommended')]
                for path in paths:
                    path.parent.mkdir()
                    path.write_bytes(b'{"old": true}')
                obj = cls.__new__(cls)
                setattr(obj, '_' + name + '__managed_policies_path', str(paths[0].parent))
                setattr(obj, '_' + name + '__recommended_policies_path', str(paths[1].parent))
                obj.policies_json = {'New': True, 'Recommended': {'Other': False}}
                with patch.object(module, 'browser_policy_values', side_effect=[{}, ValueError('recommended failed')]):
                    with self.assertRaises(ValueError):
                        obj.machine_apply()
                self.assertTrue(all(path.read_bytes() == b'{"old": true}' for path in paths))

    def test_staging_and_second_publication_failure_preserve_both_files(self):
        with TemporaryDirectory() as directory:
            paths = [Path(directory, name) for name in ('a', 'b')]
            for path in paths:
                path.write_bytes(b'old')
                path.chmod(0o640)
            contents = dict.fromkeys(paths, b'new')
            with patch('gpoa_lib.util.atomic_files.os.fsync', side_effect=OSError(28, 'disk full')):
                with self.assertRaises(OSError):
                    publish_files(contents)
            self.assertTrue(all(path.read_bytes() == b'old' for path in paths))
            replace = os.replace
            count = 0
            def fail_second(source, destination):
                nonlocal count
                count += 1
                if count == 2:
                    raise OSError('second publication failed')
                return replace(source, destination)
            with patch('gpoa_lib.util.atomic_files.os.replace', side_effect=fail_second):
                with self.assertRaises(OSError):
                    publish_files(contents)
            self.assertTrue(all(path.read_bytes() == b'old' for path in paths))
            publish_files(contents)
            self.assertTrue(all(path.read_bytes() == b'new' and path.stat().st_mode & 0o777 == 0o640 for path in paths))
            self.assertEqual([path.name for path in Path(directory).glob('.gpupdate-*')],
                             ['.gpupdate-publish.lock'])
