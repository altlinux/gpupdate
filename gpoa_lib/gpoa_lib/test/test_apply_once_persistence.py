import unittest
from types import SimpleNamespace
from unittest.mock import patch
from gpoa_lib.storage.gpp_state import GppStateManager


class ApplyOncePersistenceTest(unittest.TestCase):
    def test_marker_survives_repeated_refreshes(self):
        previous = {'uid': 'one', 'apply_once': True, 'applied': 'original timestamp'}
        for _ in range(3):
            current = {'uid': 'one', 'apply_once': True}
            obj = SimpleNamespace(**current)
            with patch('gpoa_lib.storage.gpp_state.get_previous_elements', return_value=[previous]):
                self.assertTrue(GppStateManager().should_skip(current, 'Files', obj))
            self.assertEqual(obj.applied, 'original timestamp')
            previous = vars(obj)
