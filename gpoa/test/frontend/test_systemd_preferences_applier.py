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

import tempfile
import os
import sys
import types
import importlib
import base64
import unittest
import unittest.mock
from pathlib import Path


class _storage_stub:
    def __init__(self, values=None):
        self.values = values or {}

    def get_entry(self, path, dictionary=None, preg=True):
        return self.values.get(path)

    def get_key_value(self, path):
        return None


class _manager_stub:
    def __init__(self, exists_map=None, active_state_map=None, reload_exc=None):
        self.exists_map = exists_map or {}
        self.active_state_map = active_state_map or {}
        self.reload_exc = reload_exc
        self.exists_calls = []
        self.apply_state_calls = []
        self.restart_calls = []
        self.stop_calls = []
        self.reload_calls = 0
        self.call_order = []

    def exists(self, unit_name):
        self.exists_calls.append(unit_name)
        return self.exists_map.get(unit_name, False)

    def reload(self):
        self.call_order.append('reload')
        self.reload_calls += 1
        if self.reload_exc is not None:
            raise self.reload_exc

    def active_state(self, unit_name):
        return self.active_state_map.get(unit_name, 'inactive')

    def restart(self, unit_name):
        self.call_order.append('restart:{}'.format(unit_name))
        self.restart_calls.append(unit_name)

    def stop(self, unit_name):
        self.call_order.append('stop:{}'.format(unit_name))
        self.stop_calls.append(unit_name)

    def apply_state(self, unit_name, state, now):
        self.call_order.append('apply_state:{}'.format(unit_name))
        self.apply_state_calls.append((unit_name, state, now))


def _stub_external_modules():
    """Stub heavy external dependencies not available in unit test environment."""
    if 'samba' not in sys.modules:
        samba_stub = types.ModuleType('samba')
        samba_stub.getopt = types.ModuleType('samba.getopt')
        sys.modules['samba'] = samba_stub
        sys.modules['samba.getopt'] = samba_stub.getopt

    if 'util.samba' not in sys.modules:
        util_samba = types.ModuleType('util.samba')

        class _smbopts_stub:
            def get_server_role(self):
                return 'member server'

        util_samba.smbopts = _smbopts_stub
        sys.modules['util.samba'] = util_samba

    if 'util' not in sys.modules:
        util_pkg = types.ModuleType('util')
        util_pkg.__path__ = [os.path.join(os.getcwd(), 'util')]
        sys.modules['util'] = util_pkg

    if 'gpoa' not in sys.modules:
        gpoa_stub = types.ModuleType('gpoa')
        gpoa_stub.__path__ = [os.getcwd()]
        sys.modules['gpoa'] = gpoa_stub

    if 'gpoa.messages' not in sys.modules:
        msg_stub = types.ModuleType('gpoa.messages')
        msg_stub.message_with_code = lambda code, *a, **kw: str(code)
        sys.modules['gpoa.messages'] = msg_stub


def _load_spa():
    _stub_external_modules()
    if 'frontend' not in sys.modules:
        frontend_pkg = types.ModuleType('frontend')
        frontend_pkg.__path__ = [os.path.join(os.getcwd(), 'frontend')]
        sys.modules['frontend'] = frontend_pkg
    return importlib.import_module('frontend.systemd_preferences_applier')


class SystemdPreferencesApplierTestCase(unittest.TestCase):
    def test_apply_mode_skips_non_matching_rules(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        manager = _manager_stub(exists_map={
            'exists.service': True,
            'missing.service': False,
        })
        runtime.systemd_manager = manager
        runtime.apply_rules([
            {
                'uid': '1',
                'unit': 'missing.service',
                'state': 'enable',
                'now': False,
                'apply_mode': 'if_exists',
                'policy_target': 'machine',
                'edit_mode': 'override',
                'dropin_name': '50-gpo.conf',
                'unit_file': None,
                'file_dependencies': [],
                'element_type': 'service',
            },
            {
                'uid': '2',
                'unit': 'exists.service',
                'state': 'disable',
                'now': False,
                'apply_mode': 'if_missing',
                'policy_target': 'machine',
                'edit_mode': 'override',
                'dropin_name': '50-gpo.conf',
                'unit_file': None,
                'file_dependencies': [],
                'element_type': 'service',
            },
            {
                'uid': '3',
                'unit': 'exists.service',
                'state': 'enable',
                'now': False,
                'apply_mode': 'always',
                'policy_target': 'machine',
                'edit_mode': 'override',
                'dropin_name': '50-gpo.conf',
                'unit_file': None,
                'file_dependencies': [],
                'element_type': 'service',
            },
        ])

        self.assertEqual(manager.apply_state_calls, [('exists.service', 'enable', False)])

    def test_non_applicable_rules_still_reach_phase2_candidates(self):
        # Rules that don't match apply_mode must still be checked for
        # dependency-triggered restarts (phase2_candidates).
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub(exists_map={'exists.service': True})
        runtime.apply_rules([
            {
                'uid': '1',
                'unit': 'exists.service',
                'state': 'enable',
                'now': False,
                'apply_mode': 'if_missing',
                'policy_target': 'machine',
                'edit_mode': 'create',
                'dropin_name': '50-gpo.conf',
                'unit_file': None,
                'file_dependencies': [{'mode': 'changed', 'path': '/tmp/test.ini'}],
                'element_type': 'service',
            },
        ])

        self.assertEqual(len(runtime.phase2_candidates), 1)
        self.assertEqual(runtime.phase2_candidates[0]['uid'], '1')
        # State action must not have been applied (apply_mode didn't match)
        self.assertEqual(runtime.systemd_manager.apply_state_calls, [])

    def test_non_applicable_rule_triggers_dependency_restart(self):
        # Service exists, apply_mode='if_missing' → edit skipped, but
        # dependency change must still trigger a restart.
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub(
            exists_map={'exists.service': True},
            active_state_map={'exists.service': 'active'},
        )
        runtime.apply_rules([
            {
                'uid': '1',
                'unit': 'exists.service',
                'state': 'enable',
                'now': False,
                'apply_mode': 'if_missing',
                'policy_target': 'machine',
                'edit_mode': 'create',
                'dropin_name': '50-gpo.conf',
                'unit_file': None,
                'file_dependencies': [{'mode': 'changed', 'path': '/tmp/test.ini'}],
                'element_type': 'service',
            },
        ])

        with unittest.mock.patch('frontend.systemd_preferences_applier.query', return_value=True):
            runtime.post_restart()

        self.assertIn('exists.service', runtime.systemd_manager.restart_calls)

    def test_edit_mode_create_or_override_writes_expected_paths(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub(exists_map={
            'exists.service': True,
            'new.service': False,
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime.context.systemd_dir = tmpdir
            runtime.apply_rules([
                {
                    'uid': '10',
                    'unit': 'exists.service',
                    'state': 'as_is',
                    'now': False,
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'create_or_override',
                    'dropin_name': 'custom.conf',
                    'unit_file': '[Service]\nRestart=always',
                    'file_dependencies': [],
                    'element_type': 'service',
                },
                {
                    'uid': '11',
                    'unit': 'new.service',
                    'state': 'as_is',
                    'now': False,
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'create_or_override',
                    'dropin_name': 'custom.conf',
                    'unit_file': '[Service]\nRestart=no',
                    'file_dependencies': [],
                    'element_type': 'service',
                },
            ])

            dropin_path = '{}/exists.service.d/custom.conf'.format(tmpdir)
            create_path = '{}/new.service'.format(tmpdir)
            with open(dropin_path, 'r', encoding='utf-8') as fh:
                self.assertIn('gpupdate-managed uid: 10', fh.read())
            with open(create_path, 'r', encoding='utf-8') as fh:
                self.assertIn('gpupdate-managed uid: 11', fh.read())
            self.assertGreaterEqual(runtime.systemd_manager.reload_calls, 1)

    def test_apply_rules_uses_reload_barrier_before_state_actions(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        manager = _manager_stub(exists_map={'demo.service': False})
        runtime.systemd_manager = manager

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime.context.systemd_dir = tmpdir
            runtime.apply_rules([{
                'uid': 'reload-order',
                'unit': 'demo.service',
                'state': 'enable',
                'now': True,
                'apply_mode': 'always',
                'policy_target': 'machine',
                'edit_mode': 'create',
                'dropin_name': '50-gpo.conf',
                'unit_file': '[Unit]\nDescription=Demo',
                'file_dependencies': [],
                'element_type': 'service',
            }])

        self.assertEqual(manager.call_order, ['reload', 'apply_state:demo.service'])

    def test_apply_rules_skips_state_actions_when_reload_fails(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        manager = _manager_stub(
            exists_map={'demo.service': False, 'stateonly.service': True},
            reload_exc=spa.SystemdManagerError('reload failed', action='reload'),
        )
        runtime.systemd_manager = manager

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime.context.systemd_dir = tmpdir
            runtime.apply_rules([
                {
                    'uid': 'reload-fail',
                    'unit': 'demo.service',
                    'state': 'enable',
                    'now': True,
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'create',
                    'dropin_name': '50-gpo.conf',
                    'unit_file': '[Unit]\nDescription=Demo',
                    'file_dependencies': [],
                    'element_type': 'service',
                },
                {
                    'uid': 'state-only',
                    'unit': 'stateonly.service',
                    'state': 'disable',
                    'now': False,
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'override',
                    'dropin_name': '50-gpo.conf',
                    'unit_file': None,
                    'file_dependencies': [],
                    'element_type': 'service',
                },
            ])

        self.assertEqual(manager.reload_calls, 1)
        self.assertEqual(manager.apply_state_calls, [])
        self.assertEqual(runtime.phase2_candidates, [])

    def test_normalize_rule_unescapes_newline_sequences_in_unit_file(self):
        spa = _load_spa()

        normalized = spa._normalize_rule({
            'uid': '12',
            'unit': 'escaped.service',
            'state': 'as_is',
            'now': False,
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'dropin_name': '50-gpo.conf',
            'unit_file': '[Service]\\nRestart=always',
            'file_dependencies': [],
            'element_type': 'service',
        })

        self.assertEqual(normalized['unit_file'], '[Service]\nRestart=always')

    def test_normalize_rule_maps_remove_policy_aliases(self):
        spa = _load_spa()

        normalized_legacy = spa._normalize_rule({
            'uid': 'rp-1',
            'unit': 'demo.service',
            'state': 'as_is',
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'removePolicy': '1',
        })
        normalized_snake = spa._normalize_rule({
            'uid': 'rp-2',
            'unit': 'demo.service',
            'state': 'as_is',
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'remove_policy': True,
        })

        self.assertTrue(normalized_legacy['remove_policy'])
        self.assertTrue(normalized_snake['remove_policy'])

    def test_normalize_rule_decodes_unit_file_b64_with_priority(self):
        spa = _load_spa()

        original = "[Service]\nExecStart=/bin/bash -c \"echo 'ok'\"\n"
        encoded = base64.b64encode(original.encode('utf-8')).decode('ascii')
        normalized = spa._normalize_rule({
            'uid': '13',
            'unit': 'encoded.service',
            'state': 'as_is',
            'now': False,
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'dropin_name': '50-gpo.conf',
            'unit_file_b64': encoded,
            'unit_file': '[Service]\\nExecStart=/bin/false',
            'file_dependencies': [],
            'element_type': 'service',
        })

        self.assertEqual(normalized['unit_file'], original)

    def test_normalize_rule_falls_back_to_legacy_when_unit_file_b64_invalid(self):
        spa = _load_spa()

        with unittest.mock.patch('frontend.systemd_preferences_applier.log') as log_mock:
            normalized = spa._normalize_rule({
                'uid': '14',
                'unit': 'encoded.service',
                'state': 'as_is',
                'now': False,
                'apply_mode': 'always',
                'policy_target': 'machine',
                'edit_mode': 'override',
                'dropin_name': '50-gpo.conf',
                'unit_file_b64': 'invalid-%%%',
                'unit_file': '[Service]\\nRestart=always',
                'file_dependencies': [],
                'element_type': 'service',
            })

        self.assertEqual(normalized['unit_file'], '[Service]\nRestart=always')
        log_mock.assert_any_call('W47', {
            'reason': 'Invalid unit_file_b64 payload',
            'unit': 'encoded.service',
            'uid': '14',
        })

    def test_normalize_rule_truncates_too_many_dependencies(self):
        spa = _load_spa()

        too_many = [{'mode': 'changed', 'path': '/etc/demo{}'.format(idx)} for idx in range(64)]
        normalized = spa._normalize_rule({
            'uid': '15',
            'unit': 'demo.service',
            'state': 'as_is',
            'apply_mode': 'always',
            'policy_target': 'machine',
            'dropin_name': '50-gpo.conf',
            'file_dependencies': too_many,
        })
        self.assertIsNotNone(normalized)
        self.assertEqual(len(normalized['file_dependencies']), 32)

    def test_normalize_rule_filters_invalid_dependency_paths(self):
        spa = _load_spa()

        normalized = spa._normalize_rule({
            'uid': '16',
            'unit': 'demo.service',
            'state': 'as_is',
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'dropin_name': '50-gpo.conf',
            'file_dependencies': [
                {'mode': 'changed', 'path': '/etc/demo.conf'},
                {'mode': 'changed', 'path': '../relative'},
                {'mode': 'changed', 'path': '/tmp/\ninvalid'},
            ],
        })
        self.assertEqual(normalized['file_dependencies'], [{'mode': 'changed', 'path': '/etc/demo.conf'}])

    def test_normalize_rule_rejects_oversized_unit_file(self):
        spa = _load_spa()

        huge_payload = 'A' * (spa.MAX_UNIT_FILE_SIZE + 1)
        encoded = base64.b64encode(huge_payload.encode('utf-8')).decode('ascii')
        normalized = spa._normalize_rule({
            'uid': '17',
            'unit': 'huge.service',
            'state': 'as_is',
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'dropin_name': '50-gpo.conf',
            'unit_file_b64': encoded,
        })
        self.assertIsNone(normalized['unit_file'])

    def test_post_restart_uses_dependency_modes(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub(active_state_map={'demo.service': 'active'})
        runtime.phase2_candidates = [{
            'uid': '1',
            'unit': 'demo.service',
            'state': 'as_is',
            'now': False,
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'dropin_name': '50-gpo.conf',
            'unit_file': None,
            'file_dependencies': [
                {'mode': 'changed', 'path': '/etc/demo.conf'},
                {'mode': 'presence_changed', 'path': '/etc/demo.presence'},
            ],
            'element_type': 'service',
        }]

        with unittest.mock.patch('frontend.systemd_preferences_applier.query') as query_mock:
            query_mock.side_effect = lambda path, mode='changed': mode == 'changed'
            runtime.post_restart()

        self.assertIn('demo.service', runtime.systemd_manager.restart_calls)

    def test_post_restart_skips_when_dependency_unchanged(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub(active_state_map={'demo.service': 'active'})
        runtime.phase2_candidates = [{
            'uid': '1',
            'unit': 'demo.service',
            'state': 'as_is',
            'now': False,
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'dropin_name': '50-gpo.conf',
            'unit_file': None,
            'file_dependencies': [
                {'mode': 'changed', 'path': '/etc/demo.conf'},
            ],
            'element_type': 'service',
        }]

        with unittest.mock.patch('frontend.systemd_preferences_applier.query', return_value=False):
            runtime.post_restart()

        self.assertNotIn('demo.service', runtime.systemd_manager.restart_calls)

    def test_removed_rules_detected_from_previous_snapshot(self):
        spa = _load_spa()

        storage = _storage_stub({
            'Software/BaseALT/Policies/Preferences/Machine/Systemds': str([{
                'uid': 'keep',
                'unit': 'keep.service',
                'state': 'enable',
                'apply_mode': 'always',
                'policy_target': 'machine',
                'edit_mode': 'override',
            }]),
            'Previous/Software/BaseALT/Policies/Preferences/Machine/Systemds': str([
                {
                    'uid': 'keep',
                    'unit': 'keep.service',
                    'state': 'enable',
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'override',
                },
                {
                    'uid': 'drop',
                    'unit': 'drop.service',
                    'state': 'enable',
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'override',
                },
            ]),
        })
        removed = spa._get_removed_rules(storage, 'Machine', 'machine')
        self.assertEqual(len(removed), 1)
        self.assertEqual(removed[0]['uid'], 'drop')

    def test_get_rule_sets_for_scope_includes_remove_policy_cleanup(self):
        spa = _load_spa()

        storage = _storage_stub({
            'Software/BaseALT/Policies/Preferences/Machine/Systemds': str([
                {
                    'uid': 'active',
                    'unit': 'active.service',
                    'state': 'enable',
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'override',
                    'removePolicy': '0',
                },
                {
                    'uid': 'cleanup',
                    'unit': 'cleanup.service',
                    'state': 'enable',
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'create',
                    'removePolicy': '1',
                },
            ]),
            'Previous/Software/BaseALT/Policies/Preferences/Machine/Systemds': str([]),
        })

        active_rules, cleanup_rules = spa._get_rule_sets_for_scope(storage, 'Machine', 'machine')
        self.assertEqual([rule['uid'] for rule in active_rules], ['active'])
        self.assertEqual([rule['uid'] for rule in cleanup_rules], ['cleanup'])

    def test_normalize_rule_rejects_unsafe_unit_and_dropin_paths(self):
        spa = _load_spa()

        bad_unit = {
            'uid': 'bad-unit',
            'unit': '/tmp/evil.service',
            'state': 'enable',
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
        }
        bad_dropin = {
            'uid': 'bad-dropin',
            'unit': 'safe.service',
            'state': 'enable',
            'apply_mode': 'always',
            'policy_target': 'machine',
            'edit_mode': 'override',
            'dropInName': '../../evil.conf',
        }
        self.assertIsNone(spa._normalize_rule(bad_unit))
        self.assertIsNone(spa._normalize_rule(bad_dropin))

    def test_cleanup_removed_rules_keeps_non_restartable_types_skipped(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub(active_state_map={'usb.device': 'active'})

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime.context.systemd_dir = tmpdir
            managed = os.path.join(tmpdir, 'usb.device')
            with open(managed, 'w', encoding='utf-8') as file_obj:
                file_obj.write('# gpupdate-managed uid: deadbeef\n[Unit]\nDescription=test\n')

            removed_rule = {
                'uid': 'deadbeef',
                'unit': 'usb.device',
                'dropin_name': '50-gpo.conf',
                'element_type': 'device',
            }

            runtime.cleanup_removed_rules([removed_rule])

            self.assertFalse(os.path.exists(managed))
            self.assertEqual(runtime.systemd_manager.reload_calls, 1)
            self.assertNotIn('usb.device', runtime.systemd_manager.stop_calls)

    def test_cleanup_removed_rules_requires_marker_on_first_line(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub(active_state_map={'demo.service': 'active'})

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime.context.systemd_dir = tmpdir
            managed = os.path.join(tmpdir, 'demo.service')
            with open(managed, 'w', encoding='utf-8') as file_obj:
                file_obj.write('[Unit]\n# gpupdate-managed uid: deadbeef\nDescription=test\n')

            removed_rule = {
                'uid': 'deadbeef',
                'unit': 'demo.service',
                'dropin_name': '50-gpo.conf',
                'element_type': 'service',
            }
            runtime.cleanup_removed_rules([removed_rule])

            self.assertTrue(os.path.exists(managed))
            self.assertEqual(runtime.systemd_manager.reload_calls, 0)

    def test_cleanup_removed_rules_skips_restart_when_reload_fails(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub(
            active_state_map={'demo.service': 'active'},
            reload_exc=spa.SystemdManagerError('reload failed', action='reload'),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime.context.systemd_dir = tmpdir
            managed = os.path.join(tmpdir, 'demo.service')
            with open(managed, 'w', encoding='utf-8') as file_obj:
                file_obj.write('# gpupdate-managed uid: deadbeef\n[Unit]\nDescription=test\n')

            removed_rule = {
                'uid': 'deadbeef',
                'unit': 'demo.service',
                'dropin_name': '50-gpo.conf',
                'element_type': 'service',
            }
            runtime.cleanup_removed_rules([removed_rule])

            self.assertFalse(os.path.exists(managed))
            self.assertEqual(runtime.systemd_manager.reload_calls, 1)
            self.assertEqual(runtime.systemd_manager.stop_calls, [])

    def test_write_rule_file_skips_symlink_target(self):
        spa = _load_spa()

        storage = _storage_stub()
        runtime = spa._systemd_preferences_runtime(storage, 'Machine', spa._Context(mode='machine'))
        runtime.systemd_manager = _manager_stub()

        with tempfile.TemporaryDirectory() as tmpdir:
            runtime.context.systemd_dir = tmpdir
            real_target = os.path.join(tmpdir, 'real.service')
            with open(real_target, 'w', encoding='utf-8') as file_obj:
                file_obj.write('real')

            symlink_target = os.path.join(tmpdir, 'evil.service')
            os.symlink(real_target, symlink_target)

            runtime._write_rule_file(Path(symlink_target), 'uid-1', '[Unit]\nDescription=test')
            with open(real_target, 'r', encoding='utf-8') as file_obj:
                self.assertEqual(file_obj.read(), 'real')

    def test_user_context_skips_when_user_manager_unavailable(self):
        spa = _load_spa()

        storage = _storage_stub()
        with unittest.mock.patch('frontend.systemd_preferences_applier.check_enabled', return_value=True):
            applier = spa.systemd_preferences_applier_user(storage, 'root')
            with unittest.mock.patch('os.path.exists', return_value=False):
                with unittest.mock.patch('frontend.systemd_preferences_applier._systemd_preferences_runtime.apply_rules') as apply_mock:
                    applier.user_context_apply()
                    self.assertFalse(apply_mock.called)

    def test_prime_dependency_journal_machine_watches_machine_dependencies(self):
        spa = _load_spa()

        storage = _storage_stub({
            'Software/BaseALT/Policies/Preferences/Machine/Systemds': str([{
                'uid': 'rule-1',
                'unit': 'demo.service',
                'state': 'as_is',
                'apply_mode': 'always',
                'policy_target': 'machine',
                'edit_mode': 'override',
                'file_dependencies': [
                    {'mode': 'changed', 'path': '/etc/demo.conf'},
                ],
            }]),
        })

        with unittest.mock.patch('frontend.systemd_preferences_applier.check_enabled', return_value=True):
            applier = spa.systemd_preferences_applier(storage)
            with unittest.mock.patch('frontend.systemd_preferences_applier.watch_many') as watch_many_mock:
                applier.prime_dependency_journal()
                watch_many_mock.assert_called_once_with(['/etc/demo.conf'])

    def test_prime_dependency_journal_machine_watches_global_user_dependencies(self):
        spa = _load_spa()

        storage = _storage_stub({
            'Software/BaseALT/Policies/Preferences/Machine/Systemds': str([
                {
                    'uid': 'rule-machine',
                    'unit': 'demo.service',
                    'state': 'as_is',
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'override',
                    'file_dependencies': [
                        {'mode': 'changed', 'path': '/etc/demo.conf'},
                    ],
                },
                {
                    'uid': 'rule-global-user',
                    'unit': 'demo-user.service',
                    'state': 'as_is',
                    'apply_mode': 'always',
                    'policy_target': 'user',
                    'edit_mode': 'override',
                    'file_dependencies': [
                        {'mode': 'changed', 'path': '/etc/demo-user.conf'},
                    ],
                },
            ]),
        })

        with unittest.mock.patch('frontend.systemd_preferences_applier.check_enabled', return_value=True):
            applier = spa.systemd_preferences_applier(storage)
            with unittest.mock.patch('frontend.systemd_preferences_applier.watch_many') as watch_many_mock:
                applier.prime_dependency_journal()
                watch_many_mock.assert_called_once_with(['/etc/demo.conf', '/etc/demo-user.conf'])

    def test_prime_dependency_journal_skips_remove_policy_rules(self):
        spa = _load_spa()

        storage = _storage_stub({
            'Software/BaseALT/Policies/Preferences/Machine/Systemds': str([{
                'uid': 'rule-removed',
                'unit': 'demo.service',
                'state': 'as_is',
                'apply_mode': 'always',
                'policy_target': 'machine',
                'edit_mode': 'override',
                'removePolicy': '1',
                'file_dependencies': [
                    {'mode': 'changed', 'path': '/etc/demo.conf'},
                ],
            }]),
        })

        with unittest.mock.patch('frontend.systemd_preferences_applier.check_enabled', return_value=True):
            applier = spa.systemd_preferences_applier(storage)
            with unittest.mock.patch('frontend.systemd_preferences_applier.watch_many') as watch_many_mock:
                applier.prime_dependency_journal()
                watch_many_mock.assert_called_once_with([])

    def test_prime_dependency_journal_user_watches_machine_and_user_dependencies(self):
        spa = _load_spa()

        storage = _storage_stub({
            'Software/BaseALT/Policies/Preferences/alice/Systemds': str([
                {
                    'uid': 'rule-machine',
                    'unit': 'demo.service',
                    'state': 'as_is',
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'override',
                    'file_dependencies': [
                        {'mode': 'changed', 'path': '/etc/demo.conf'},
                    ],
                },
                {
                    'uid': 'rule-user',
                    'unit': 'demo.service',
                    'state': 'as_is',
                    'apply_mode': 'always',
                    'policy_target': 'user',
                    'edit_mode': 'override',
                    'file_dependencies': [
                        {'mode': 'changed', 'path': '%HOME%/.config/demo.conf'},
                    ],
                },
            ]),
        })

        with unittest.mock.patch('frontend.systemd_preferences_applier.check_enabled', return_value=True):
            with unittest.mock.patch('frontend.systemd_preferences_applier.get_uid_by_username', return_value=1000):
                with unittest.mock.patch('frontend.systemd_preferences_applier.get_homedir', return_value='/home/alice'):
                    applier = spa.systemd_preferences_applier_user(storage, 'alice')
                    with unittest.mock.patch('frontend.systemd_preferences_applier.watch_many') as watch_many_mock:
                        applier.prime_dependency_journal()
                        expected_user_path = spa._expand_windows_var('%HOME%/.config/demo.conf', username='alice')
                        watch_many_mock.assert_called_once_with(['/etc/demo.conf', expected_user_path])

    def test_apply_uses_cleanup_rules_for_remove_policy_items(self):
        spa = _load_spa()

        storage = _storage_stub({
            'Software/BaseALT/Policies/Preferences/Machine/Systemds': str([
                {
                    'uid': 'cleanup',
                    'unit': 'cleanup.service',
                    'state': 'enable',
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'create',
                    'removePolicy': '1',
                },
            ]),
            'Previous/Software/BaseALT/Policies/Preferences/Machine/Systemds': str([]),
        })

        with unittest.mock.patch('frontend.systemd_preferences_applier.check_enabled', return_value=True):
            with unittest.mock.patch('frontend.systemd_preferences_applier._systemd_preferences_runtime') as runtime_ctor:
                runtime = unittest.mock.Mock()
                global_runtime = unittest.mock.Mock()
                runtime_ctor.side_effect = [runtime, global_runtime]

                applier = spa.systemd_preferences_applier(storage)
                applier.apply()

                runtime.apply_rules.assert_called_once_with([])
                cleanup_arg = runtime.cleanup_removed_rules.call_args[0][0]
                self.assertEqual(len(cleanup_arg), 1)
                self.assertEqual(cleanup_arg[0]['uid'], 'cleanup')
                global_runtime.apply_rules.assert_called_once_with([])
                global_runtime.cleanup_removed_rules.assert_called_once_with([])

    def test_machine_apply_routes_global_user_rules_to_global_context(self):
        spa = _load_spa()

        storage = _storage_stub({
            'Software/BaseALT/Policies/Preferences/Machine/Systemds': str([
                {
                    'uid': 'machine-rule',
                    'unit': 'machine.service',
                    'state': 'enable',
                    'apply_mode': 'always',
                    'policy_target': 'machine',
                    'edit_mode': 'create',
                },
                {
                    'uid': 'global-user-rule',
                    'unit': 'global-user.service',
                    'state': 'enable',
                    'apply_mode': 'always',
                    'policy_target': 'user',
                    'edit_mode': 'create',
                },
            ]),
            'Previous/Software/BaseALT/Policies/Preferences/Machine/Systemds': str([]),
        })

        with unittest.mock.patch('frontend.systemd_preferences_applier.check_enabled', return_value=True):
            with unittest.mock.patch('frontend.systemd_preferences_applier._systemd_preferences_runtime') as runtime_ctor:
                runtime = unittest.mock.Mock()
                global_runtime = unittest.mock.Mock()
                runtime_ctor.side_effect = [runtime, global_runtime]

                applier = spa.systemd_preferences_applier(storage)
                applier.apply()

                self.assertEqual(runtime_ctor.call_args_list[0][0][2].mode, 'machine')
                self.assertEqual(runtime_ctor.call_args_list[1][0][2].mode, 'global_user')
                runtime.apply_rules.assert_called_once_with([
                    unittest.mock.ANY,
                ])
                self.assertEqual(runtime.apply_rules.call_args[0][0][0]['uid'], 'machine-rule')
                global_runtime.apply_rules.assert_called_once_with([
                    unittest.mock.ANY,
                ])
                self.assertEqual(global_runtime.apply_rules.call_args[0][0][0]['uid'], 'global-user-rule')


if __name__ == '__main__':
    unittest.main()
