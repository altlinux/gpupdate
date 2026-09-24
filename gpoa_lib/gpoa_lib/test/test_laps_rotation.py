from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from gpoa_lib.frontend.laps_applier import laps_applier


class RotationTests(unittest.TestCase):
    def make_applier(self):
        item = laps_applier.__new__(laps_applier)
        item.target_user = 'managed'
        item._write_dconf_pass_last_mod = Mock()
        return item

    def test_chpasswd_failure_does_not_advance_marker(self):
        errors = (subprocess.CalledProcessError(1, ['chpasswd']),
                  subprocess.TimeoutExpired(['chpasswd'], 15), FileNotFoundError())
        for error in errors:
            item = self.make_applier()
            with patch('gpoa_lib.frontend.laps_applier.subprocess.run', side_effect=error):
                self.assertFalse(item._change_user_password('secret'))
            item._write_dconf_pass_last_mod.assert_not_called()

    def test_success_advances_marker(self):
        item = self.make_applier()
        with patch('gpoa_lib.frontend.laps_applier.subprocess.run'):
            self.assertTrue(item._change_user_password('secret'))
        item._write_dconf_pass_last_mod.assert_called_once()

    def test_failed_ldap_first_rotation_is_retryable(self):
        with TemporaryDirectory() as directory:
            item = self.make_applier()
            item._pending_rotation_path = Mock(return_value=Path(directory) / 'pending')
            item._is_password_expired = Mock(return_value=True)
            item._generate_password = Mock(return_value='secret')
            item._create_password_blob = Mock(return_value=b'encrypted')
            item._update_ldap_password = Mock(return_value=True)
            item._change_user_password = Mock(return_value=False)
            item._perform_post_action = Mock()
            self.assertFalse(item.update_laps_password())
            item._is_password_expired.return_value = False
            self.assertEqual(item._should_update_password(), (True, False))
            item._change_user_password.return_value = True
            self.assertTrue(item.update_laps_password())
            self.assertFalse(item._pending_rotation_path().exists())
            item._perform_post_action.assert_not_called()
