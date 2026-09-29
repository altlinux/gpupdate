import os
import shutil
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from gpoa_lib.frontend_plugins import gdm_resource as resource
from gpoa_lib.frontend_plugins.dm_applier import DMApplier


@unittest.skipUnless(shutil.which('gresource') and shutil.which('glib-compile-resources'),
                     'GLib resource tools are required')
class GDMResourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.target = self.directory / 'theme.gresource'
        self.background = self.directory / 'background #1.png'
        self.background.write_bytes(b'image')
        self.entries = {
            '/org/gnome/shell/theme/gnome-shell-dark.css':
                b'#lockDialogGroup { background: url(resource:///old.png); color: white; }',
            '/org/gnome/shell/theme/gnome-shell-light.css':
                b'#lockDialogGroup { background-color: #222226; }\n.other { color: red; }',
            '/org/gnome/shell/theme/a/image.png': b'\x00\xff\x80binary\r\n',
            '/another/prefix/image.png': b'another\x00image',
            '/another/prefix/a&b.svg': b'<svg/>',
        }
        resource.compile_resources(self.entries, self.directory, self.target)
        self.target.chmod(0o640)
        self.original = self.target.read_bytes()

    def test_both_themes_binary_aliases_metadata_and_repeated_application(self):
        resource.apply_background(self.target, self.background)
        updated = resource.read_resources(self.target)
        self.assertEqual(set(updated), set(self.entries))
        for alias, data in updated.items():
            if alias.endswith('.css'):
                self.assertIn(self.background.as_uri().encode(), data)
                self.assertNotIn(b'file:////', data)
            else:
                self.assertEqual(data, self.entries[alias])
        self.assertIn(b'background-color: #222226;', updated[
            '/org/gnome/shell/theme/gnome-shell-light.css'])
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.target.stat().st_uid, os.getuid())
        backup = Path(str(self.target) + '.backup')
        self.assertEqual(backup.read_bytes(), self.original)
        published = self.target.read_bytes()
        resource.apply_background(self.target, self.background)
        self.assertEqual(self.target.read_bytes(), published)
        self.assertEqual(backup.read_bytes(), self.original)
        resource.restore_background(self.target)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_failed_compile_or_publish_preserves_installed_resource(self):
        for operation in ('compile_resources', '_publish'):
            with patch.object(resource, operation, side_effect=OSError('injected failure')):
                with self.assertRaises(OSError):
                    resource.apply_background(self.target, self.background)
            self.assertEqual(self.target.read_bytes(), self.original)
            self.assertEqual(list(self.directory.glob('.gpupdate-*')), [])

    def test_invalid_backup_does_not_replace_working_theme(self):
        Path(str(self.target) + '.backup').write_bytes(b'not a resource')
        with self.assertRaises((subprocess.CalledProcessError, ValueError)):
            resource.restore_background(self.target)
        self.assertEqual(self.target.read_bytes(), self.original)

    def test_incomplete_theme_is_not_published(self):
        incomplete = dict(self.entries)
        incomplete['/org/gnome/shell/theme/gnome-shell-light.css'] = b'.other { color: red; }'
        with self.assertRaises(ValueError):
            resource.update_background(incomplete, self.background)

    def test_concurrent_updates_keep_original_backup(self):
        other = self.directory / 'second.png'
        other.write_bytes(b'other image')
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(resource.apply_background, self.target, path)
                       for path in (self.background, other)]
            for future in futures:
                future.result(timeout=20)
        current = resource.read_resources(self.target)
        css = current['/org/gnome/shell/theme/gnome-shell-light.css']
        self.assertTrue(any(path.as_uri().encode() in css for path in (self.background, other)))
        self.assertEqual(Path(str(self.target) + '.backup').read_bytes(), self.original)

    def test_plugin_reports_generation_failures_and_success(self):
        obj = DMApplier({'Software/BaseALT/Policies/DisplayManager':
                         {'Greeter.Background': str(self.background)}})
        with patch.object(obj, 'detect_dm', return_value={'available': ['gdm'], 'active': 'gdm'}), \
                patch.object(obj, '_find_gnome_shell_gresource', return_value=str(self.target)):
            self.assertEqual(obj.run().status, 'applied')
            with patch.object(resource, 'compile_resources', side_effect=OSError('compiler failed')):
                obj.background_source = str(self.directory / 'different.png')
                Path(obj.background_source).write_bytes(b'image')
                before = self.target.read_bytes()
                self.assertEqual(obj.run().status, 'failed')
                self.assertEqual(self.target.read_bytes(), before)
