import unittest
from types import SimpleNamespace
from unittest.mock import patch
from gpoa_lib.storage.gpp_state import GppStateManager, merge_applied_markers
from gpoa_lib.storage.dconf_registry import Dconf_registry
import json


class ApplyOncePersistenceTest(unittest.TestCase):
    def test_child_marker_updates_only_matching_current_object(self):
        parent = SimpleNamespace(uid='one', apply_once=True, policy_guid='gpo')
        other = SimpleNamespace(uid='two', apply_once=True, policy_guid='gpo')
        child = SimpleNamespace(**vars(parent))
        state = GppStateManager('alice')
        state.mark_applied(vars(child), 'Folders', child)
        self.assertFalse(hasattr(parent, 'applied'))
        with patch.object(Dconf_registry, 'folders', [parent, other]):
            merge_applied_markers(json.loads(json.dumps(state.applied_markers)))
        self.assertEqual(parent.applied, child.applied)
        self.assertFalse(hasattr(other, 'applied'))

    def test_marker_survives_repeated_refreshes(self):
        previous = {'uid': 'one', 'apply_once': True, 'applied': 'original timestamp'}
        for _ in range(3):
            current = {'uid': 'one', 'apply_once': True}
            obj = SimpleNamespace(**current)
            with patch('gpoa_lib.storage.gpp_state.get_previous_elements', return_value=[previous]):
                self.assertTrue(GppStateManager().should_skip(current, 'Files', obj))
            self.assertEqual(obj.applied, 'original timestamp')
            previous = vars(obj)
