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
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gpoa_lib.util.ipacreds import ipacreds

try:
    from ipalib.ipajson import json_decode_binary
except ImportError:
    json_decode_binary = None


class FreeIPAChainResponseTest(unittest.TestCase):
    def setUp(self):
        self.credentials = ipacreds.__new__(ipacreds)
        self.credentials.get_server = Mock(return_value='ipa.example.test')
        self.credentials.get_machine_name = Mock(return_value='client.example.test')
        self.rpc = Mock()
        self.host_command, self.user_command = Mock(), Mock()
        self.api = SimpleNamespace(
            isdone=lambda stage: True,
            Backend=SimpleNamespace(rpcclient=self.rpc),
            Command=SimpleNamespace(chain_resolve_for_host=self.host_command,
                                    chain_resolve_for_user=self.user_command))
        module = ModuleType('ipalib')
        module.api = self.api
        self.cache_read = Mock(return_value={})
        for patcher in (
            patch.dict(sys.modules, {'ipalib': module}),
            patch('gpoa_lib.util.ipacreds.Dconf_registry.get_dictionary_from_dconf_file_db',
                  self.cache_read),
            patch('gpoa_lib.util.ipacreds.extract_display_name_version', return_value={}),
            patch('gpoa_lib.util.ipacreds.get_uid_by_username', return_value=1000),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.policy = {'name': 'Test policy', 'version': 2, 'flags': 0,
                       'file_system_path': '\\\\ipa.example.test\\sysvol\\'
                                           '{9533406A-01C1-47E7-8097-EB153835E192}',
                       'link': 'host'}

    def _run_for_both_targets(self, response, expected_count):
        self.host_command.return_value = response
        self.user_command.return_value = response
        for username in ('client.example.test', 'alice'):
            with self.subTest(username=username, response=response):
                result, server = self.credentials.update_gpos(username)
                self.assertEqual(expected_count, len(result))
                self.assertEqual('ipa.example.test', server)
                if result:
                    self.assertEqual(self.policy['file_system_path'], result[0].file_sys_path)
                    self.assertEqual(2, result[0].version)
                self.rpc.disconnect.assert_called()

    def test_list_and_tuple_chains_including_successful_empty_response(self):
        for constructor in (list, tuple):
            for policies in ([], [self.policy]):
                self._run_for_both_targets({'result': constructor(policies)}, len(policies))

    @unittest.skipUnless(json_decode_binary, 'FreeIPA JSON decoder unavailable')
    def test_real_freeipa_decoding_preserves_empty_and_nonempty_chains(self):
        for policies in ([], [self.policy]):
            response = json_decode_binary(json.dumps({'result': policies}))
            self.assertIsInstance(response['result'], tuple)
            self._run_for_both_targets(response, len(policies))

    def test_invalid_response_and_missing_server_are_not_empty_success(self):
        for target in (self.host_command, self.user_command):
            username = 'alice' if target is self.user_command else 'client.example.test'
            for invalid in (None, {}, 'not a chain', 1):
                with self.subTest(username=username, invalid=invalid):
                    target.return_value = {'result': invalid}
                    with self.assertRaisesRegex(ValueError, 'Invalid FreeIPA policy chain response'):
                        self.credentials.update_gpos(username)
            target.return_value = {'result': ()}
            self.credentials.get_server.return_value = None
            with self.assertRaisesRegex(ValueError, 'policy server is unavailable'):
                self.credentials.update_gpos(username)
            self.credentials.get_server.return_value = 'ipa.example.test'
        self.cache_read.assert_not_called()

    def test_rpc_failure_propagates_and_disconnects_without_reading_cache(self):
        for target in (self.host_command, self.user_command):
            self.rpc.reset_mock()
            target.side_effect = OSError('RPC unavailable')
            username = 'alice' if target is self.user_command else 'client.example.test'
            with self.assertRaisesRegex(OSError, 'RPC unavailable'):
                self.credentials.update_gpos(username)
            self.rpc.disconnect.assert_called_once_with()
        self.cache_read.assert_not_called()
