#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT_DIR = Path(__file__).resolve().parents[2]
FACILITY = ROOT_DIR / 'dist' / 'gpupdate-ssh'
PAM_CONFIG = ROOT_DIR / 'dist' / 'system-policy-gpupdate'
CONTROL_FUNCTIONS = Path('/etc/control.d/functions')


@unittest.skipUnless(CONTROL_FUNCTIONS.exists(), 'ALT control is not installed')
class GpupdateSshControlTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.config = temp_path / 'system-policy-gpupdate'
        self.script = temp_path / 'gpupdate-ssh'

        self.config.write_text(PAM_CONFIG.read_text(encoding='utf-8'), encoding='utf-8')
        facility = FACILITY.read_text(encoding='utf-8').replace(
            'CONFIG=/etc/pam.d/system-policy-gpupdate',
            f'CONFIG={self.config}',
        )
        self.script.write_text(facility, encoding='utf-8')
        self.script.chmod(0o755)

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_control(self, *args):
        return subprocess.run(
            [os.fspath(self.script), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_lists_numeric_mapping_order(self):
        result = self.run_control('list')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), 'disabled enabled')

    def test_switches_both_ways_and_is_idempotent(self):
        self.assertEqual(self.run_control('status').stdout.strip(), 'enabled')

        result = self.run_control('disabled')
        self.assertEqual(result.returncode, 0, result.stderr)
        disabled_content = self.config.read_text(encoding='utf-8')
        self.assertIn('service in systemd-user:sshd quiet', disabled_content)
        self.assertEqual(self.run_control('status').stdout.strip(), 'disabled')

        result = self.run_control('disabled')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.config.read_text(encoding='utf-8'),
            disabled_content,
        )

        result = self.run_control('enabled')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            'service = systemd-user quiet',
            self.config.read_text(encoding='utf-8'),
        )
        self.assertEqual(self.run_control('status').stdout.strip(), 'enabled')

    def test_rejects_unknown_pam_condition(self):
        content = self.config.read_text(encoding='utf-8').replace(
            'service = systemd-user',
            'service = custom-service',
        )
        self.config.write_text(content, encoding='utf-8')

        result = self.run_control('disabled')

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unsupported configuration', result.stderr)
        self.assertEqual(self.config.read_text(encoding='utf-8'), content)
