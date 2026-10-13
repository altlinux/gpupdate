"""Regression checks for the shipped boot ordering, not a live boot test."""
import configparser
from pathlib import Path
import unittest


class BootOrderingTest(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[2] / 'dist/gpupdate.service'
        self.unit = configparser.ConfigParser(interpolation=None)
        self.unit.read(path)

    def dependencies(self, name):
        return set(self.unit['Unit'].get(name, '').split())

    def test_logind_starts_before_policy_application(self):
        self.assertIn('systemd-logind.service', self.dependencies('After'))
        self.assertIn('systemd-logind.service', self.dependencies('Wants'))
        self.assertNotIn('systemd-logind.service', self.dependencies('Before'))

    def test_graphical_login_waits_for_policy_application(self):
        self.assertIn('display-manager.service', self.dependencies('Before'))

    def test_policy_application_keeps_its_startup_prerequisites(self):
        self.assertEqual(self.unit['Service']['Type'], 'oneshot')
        self.assertEqual(self.unit['Service']['ExecStart'], '/usr/bin/gpupdate')
        self.assertTrue({'network-online.target', 'sssd.service',
                         'oddjobd.service'} <= self.dependencies('After'))
        self.assertIn('oddjobd.service', self.dependencies('Wants'))
        self.assertIn('multi-user.target',
                      self.unit['Install']['WantedBy'].split())


if __name__ == '__main__':
    unittest.main()
