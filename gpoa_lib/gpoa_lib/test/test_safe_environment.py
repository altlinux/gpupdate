import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gpoa_lib.util.safe_file import open_regular_file
from gpoa_lib.frontend.envvar_applier import envvar_applier_user
from gpoa_lib.frontend.appliers.envvar import Envvar


class SafeEnvironmentTest(unittest.TestCase):
    def test_regeneration_retains_only_requested_once_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / '.gpupdate_environment'
            target.write_text('ONCE DEFAULT="original value"\nREPEATED DEFAULT="old"\n')
            with patch('gpoa_lib.frontend.appliers.envvar.get_homedir', return_value=tmp):
                for _ in range(3):
                    Envvar.clear_envvar_file('alice', keep_names={'ONCE'})
                    self.assertEqual(target.read_text(), 'ONCE DEFAULT="original value"\n')
                Envvar.clear_envvar_file('alice')
                self.assertEqual(target.read_text(), '')

    def test_link_targets_are_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            target.write_text('keep')
            link = Path(tmp) / 'environment'
            for hard in (False, True):
                if hard:
                    os.link(target, link)
                else:
                    link.symlink_to(target)
                with self.assertRaises((OSError, ValueError)):
                    with open_regular_file(link, 'w'):
                        pass
                self.assertEqual(target.read_text(), 'keep')
                link.unlink()
            with open_regular_file(link, 'w') as stream:
                stream.write('NAME DEFAULT="value"\n')
            self.assertEqual(link.read_text(), 'NAME DEFAULT="value"\n')

    def test_disabled_applier_does_not_clear_environment(self):
        storage = Mock()
        storage.get_envvars.return_value = []
        with patch('gpoa_lib.frontend.envvar_applier.check_enabled', return_value=False), \
                patch('gpoa_lib.frontend.envvar_applier.Envvar.clear_envvar_file') as clear:
            applier = envvar_applier_user(storage, 'alice')
            applier.admin_context_apply()
            clear.assert_not_called()
