#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#

import unittest
from unittest.mock import Mock, patch

from gpoa_lib.frontend.file_applier import file_applier_user


class FileApplierHomeTestCase(unittest.TestCase):
    @patch('gpoa_lib.frontend.file_applier.homedir_exists', return_value=False)
    def test_missing_home_skips_before_file_processing(self, home_exists):
        applier = file_applier_user.__new__(file_applier_user)
        applier.username = 'domain-user'
        applier._file_applier_user__module_enabled = True
        applier.run = Mock()

        result = applier.admin_context_apply()

        home_exists.assert_called_once_with('domain-user')
        applier.run.assert_not_called()
        self.assertEqual(result.status, 'skipped')
        self.assertIn('home directory', result.error)
