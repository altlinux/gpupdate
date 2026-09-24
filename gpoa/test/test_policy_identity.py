import unittest
from unittest.mock import patch

import backend
from gpoa_lib.util.util import get_policy_uid


class PolicyIdentityTests(unittest.TestCase):
    def test_missing_and_root_accounts_are_not_machine_targets(self):
        for uid in (None, 0):
            with patch('gpoa_lib.util.util.get_uid_by_username', return_value=uid):
                with self.assertRaises(ValueError):
                    get_policy_uid('user')
                self.assertIsNone(get_policy_uid('computer', True))

    def test_save_rejects_unresolved_user_before_writes(self):
        for save in (backend.save_dconf, backend.save_dconf_without_previous):
            with patch.object(backend, 'get_policy_uid', side_effect=ValueError), \
                    patch.object(backend, 'touch_file') as touch:
                with self.assertRaises(ValueError):
                    save('missing', False)
                touch.assert_not_called()

    def test_factory_validates_before_selecting_backend(self):
        with patch.object(backend, 'get_policy_uid', side_effect=ValueError), \
                patch.object(backend, 'GPConfig') as config:
            with self.assertRaises(ValueError):
                backend.backend_factory(None, 'missing', False, True)
            config.assert_not_called()

    def test_validated_uid_is_reused(self):
        with patch.object(backend, 'get_policy_uid') as resolve:
            self.assertEqual(backend._save_uid('user', False, 10001), 10001)
            resolve.assert_not_called()
