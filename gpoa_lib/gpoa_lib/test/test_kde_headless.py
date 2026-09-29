import importlib
import os
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

kde = importlib.import_module('gpoa_lib.frontend.kde_applier')


class KdeHeadlessTest(unittest.TestCase):
    def setUp(self):
        self.version = patch.object(kde.kde_applier_user, 'kde_version', None)
        self.version.start()
        self.addCleanup(self.version.stop)

    def test_probe_is_headless_and_does_not_change_parent_environment(self):
        for version in (5, 6):
            with self.subTest(version=version), patch.dict(os.environ, {'QT_QPA_PLATFORM': 'wayland'}), \
                    patch.object(kde.shutil, 'which', side_effect=lambda name, **kw: '/usr/bin/' + name), \
                    patch.object(kde.subprocess, 'check_output', return_value=f'KDE Frameworks Version: {version}.10.0') as probe:
                self.assertEqual(kde.get_kde_version(), version)
                self.assertEqual(probe.call_args.kwargs['env']['QT_QPA_PLATFORM'], 'offscreen')
                self.assertEqual(os.environ['QT_QPA_PLATFORM'], 'wayland')
                self.assertEqual(probe.call_args.kwargs['timeout'], 15)

    def test_failed_probe_only_falls_back_to_an_unambiguous_writer(self):
        for writers, expected in (([5], 5), ([6], 6), ([5, 6], None), ([], None)):
            names = ['kinfo'] + [f'kwriteconfig{v}' for v in writers]
            with self.subTest(writers=writers), \
                    patch.object(kde.shutil, 'which', side_effect=lambda name, **kw: name if name in names else None), \
                    patch.object(kde.subprocess, 'check_output', side_effect=subprocess.CalledProcessError(1, 'kinfo')):
                self.assertEqual(kde.get_kde_version(), expected)

    def make_applier(self):
        storage = Mock()
        storage.filter_hkcu_entries.return_value = [SimpleNamespace(
            keyname='Software/BaseALT/Policies/KDE/kwinrc/Compositing', valuename='Enabled', data='false')]
        storage.get_entry.return_value = None
        with patch.object(kde, 'check_enabled', return_value=True):
            obj = kde.kde_applier_user(storage, 'user')
        obj.locks_settings = []
        return obj

    def test_failed_detection_does_not_write_settings(self):
        obj = self.make_applier()
        with patch.object(kde, 'get_kde_version', return_value=None), patch.object(kde, 'apply') as apply:
            self.assertEqual(obj.user_context_apply().status, 'failed')
            apply.assert_not_called()

    def test_writer_failure_is_not_reported_as_applied(self):
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as home, \
                    patch.object(kde, 'get_homedir', return_value=home), \
                    patch.object(kde, 'get_kde_version', return_value=6), \
                    patch.object(kde, 'call_dbus_method'), \
                    patch.object(kde.subprocess, 'run', side_effect=OSError('writer failed') if failed else None) as run:
                obj = self.make_applier()
                self.assertEqual(obj.user_context_apply().status, 'failed' if failed else 'applied')
                self.assertEqual(run.call_args.args[0][0], 'kwriteconfig6')
