import json
from unittest import TestCase
from unittest.mock import Mock, patch
from frontend.shortcut_applier import shortcut_applier_user
from gpt.shortcuts import shortcut
from gpoa_lib.storage.dconf_registry import Dconf_registry
from gpoa_lib.storage.gpp_state import merge_applied_markers


class MergedShortcutLifecycleTest(TestCase):
    def test_user_owned_marker_survives_refresh_without_machine_stamp(self):
        machine = shortcut(dest='/tmp/link', path='/bin/true', arguments='', name='test', action='R')
        machine.uid, machine.policy_guid, machine.apply_once = 'one', 'machine-gpo', True
        machine.applied = 'machine stamp must not be borrowed'
        storage = Mock()
        storage.get_dictionary_from_dconf_file_db.return_value = {
            'Software/BaseALT/Policies/Preferences/Machine': {'Shortcuts': repr([dict(machine)])}}
        storage.get_shortcuts.side_effect = lambda user: list(Dconf_registry.shortcuts)
        storage.get_key_value.return_value = 1
        previous = []
        with patch.object(Dconf_registry, 'shortcuts', []), \
             patch('frontend.shortcut_applier.check_enabled', return_value=True), \
             patch('frontend.shortcut_applier._filter_objects', side_effect=lambda objects, user: objects), \
             patch('gpoa_lib.storage.gpp_state.get_previous_elements', side_effect=lambda *args: previous), \
             patch('frontend.shortcut_applier.expand_windows_var', side_effect=lambda value, user: value), \
             patch('frontend.shortcut_applier.apply_shortcut') as apply:
            for refresh in range(3):
                Dconf_registry.shortcuts = []
                applier = shortcut_applier_user(storage, 'alice')
                self.assertEqual(len(Dconf_registry.shortcuts), 1)
                parent = Dconf_registry.shortcuts[0]
                self.assertFalse(hasattr(parent, 'applied'))
                applier.run(True)
                merge_applied_markers(json.loads(json.dumps(applier.state_manager.applied_markers)))
                self.assertTrue(parent.applied)
                self.assertNotEqual(parent.applied, machine.applied)
                previous = [dict(parent)]
            self.assertEqual(apply.call_count, 1)
            # A second user's lifecycle is independent.
            previous = []
            Dconf_registry.shortcuts = []
            shortcut_applier_user(storage, 'bob').run(True)
            self.assertEqual(apply.call_count, 2)
