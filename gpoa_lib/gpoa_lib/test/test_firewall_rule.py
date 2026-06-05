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

from gpoa_lib.frontend.appliers.firewall_rule import getprops, get_ports, FirewallRule


class GetPropsTestCase(unittest.TestCase):

    def test_action_allow(self):
        result = getprops(['Action=Allow'])
        self.assertEqual(result['action'], 'allow')

    def test_protocol_tcp(self):
        result = getprops(['Protocol=tcp'])
        self.assertEqual(result['protocol'], 'tcp')

    def test_dir_in(self):
        result = getprops(['Dir=In'])
        self.assertEqual(result['dir'], 'in')

    def test_unknown_ignored(self):
        result = getprops(['Foo=Bar'])
        self.assertNotIn('foo', result)
        self.assertNotIn('action', result)


class GetPortsTestCase(unittest.TestCase):

    def test_single_port(self):
        result = get_ports(['LPort=80'])
        self.assertEqual(result, ['80'])

    def test_multiple_ports(self):
        result = get_ports(['LPort=80', 'LPort=443'])
        self.assertEqual(result, ['80', '443'])

    def test_no_port(self):
        result = get_ports(['Action=Allow'])
        self.assertEqual(result, [])


class FirewallRuleTestCase(unittest.TestCase):

    def test_init_parses_pipe_data(self):
        data = 'v1|Action=Allow|Protocol=tcp|Dir=In|LPort=22'
        rule = FirewallRule(data)
        self.assertEqual(rule.version, 'v1')
        self.assertEqual(rule.properties['action'], 'allow')
        self.assertEqual(rule.ports, ['22'])

    @patch('gpoa_lib.frontend.appliers.firewall_rule.subprocess.Popen')
    def test_apply_allow_action(self, mock_popen_cls):
        proc = MagicMock()
        proc.__enter__ = MagicMock(return_value=proc)
        proc.__exit__ = MagicMock(return_value=False)
        proc.wait.return_value = 0
        mock_popen_cls.return_value = proc

        rule = FirewallRule('v1|Action=Allow|LPort=80')
        rule.apply()

        called_cmd = mock_popen_cls.call_args[0][0]
        expected = ['/usr/bin/alterator-net-iptables', 'write', '-m', 'host', '-t', '80', '-u', '80']
        self.assertEqual(called_cmd, expected)

    @patch('gpoa_lib.frontend.appliers.firewall_rule.subprocess.Popen')
    def test_apply_deny_action(self, mock_popen_cls):
        proc = MagicMock()
        proc.__enter__ = MagicMock(return_value=proc)
        proc.__exit__ = MagicMock(return_value=False)
        proc.wait.return_value = 0
        mock_popen_cls.return_value = proc

        rule = FirewallRule('v1|Action=Deny|LPort=80')
        rule.apply()

        called_cmd = mock_popen_cls.call_args[0][0]
        expected = ['/usr/bin/alterator-net-iptables', 'write', '-m', 'host', '-t', '80', '-u', '80']
        self.assertEqual(called_cmd, expected)
