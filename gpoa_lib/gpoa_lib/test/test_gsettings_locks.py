from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gpoa_lib.frontend.gsettings_applier import gsettings_applier
from gpoa_lib.frontend.appliers.gsettings import system_gsettings


class GSettingsLocksTest(unittest.TestCase):
    def test_lock_changes_are_independent_of_schema(self):
        with TemporaryDirectory() as root:
            path = Path(root)
            settings = system_gsettings(str(path / 'override'))
            settings._system_gsettings__path_local_dir = str(path / 'local')
            settings._system_gsettings__path_locks = str(path / 'locks')
            settings._system_gsettings__path_profile = str(path / 'profile')
            item = Mock(schema='test')
            settings.gsettings = [item]
            with patch('gpoa_lib.frontend.appliers.gsettings.Gio'):
                for lock, changed in ((False, True), (True, True), (True, False), (False, True)):
                    item.apply.side_effect = lambda s, c, locks: locks.extend(['/test/key'] if lock else [])
                    settings.apply()
                    self.assertEqual(changed, settings.locks_changed)
                    self.assertEqual('/test/key\n' if lock else '', (path / 'locks').read_text())

    def test_standalone_lock_change_compiles_without_schema_rebuild(self):
        with TemporaryDirectory() as root:
            path = Path(root) / 'override'
            path.write_text('same')
            applier = gsettings_applier.__new__(gsettings_applier)
            applier.override_old_file = str(Path(root) / 'old')
            applier.gsettings_locks = []
            applier.gsettings_keys = []
            applier.gsettings = SimpleNamespace(override_file_path=str(path), locks_changed=True)
            applier.gsettings.apply = lambda: Path(applier.gsettings.override_file_path).write_text('same')
            with patch.object(applier, '_needs_recompile', return_value=False), \
                    patch('gpoa_lib.frontend.gsettings_applier.Dconf_registry.dconf_update') as compile_db, \
                    patch('gpoa_lib.frontend.gsettings_applier.subprocess.run') as compile_schemas:
                applier.run()
                compile_db.assert_called_once_with()
                compile_schemas.assert_not_called()
                self.assertEqual(str(path), applier.gsettings.override_file_path)
