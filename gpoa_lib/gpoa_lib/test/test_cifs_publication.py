import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from gpoa_lib.frontend.cifs_applier import cifs_applier, cifs_applier_user


class CifsPublicationTest(unittest.TestCase):
    def test_failed_preparation_preserves_maps(self):
        obj = cifs_applier_user.__new__(cifs_applier_user)
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / 'first', Path(tmp) / 'second'
            first.write_text('old1')
            second.write_text('old2')
            with self.assertRaises(TypeError):
                obj._publish_maps({first: 'new1', second: object()})
            self.assertEqual(first.read_text(), 'old1')
            self.assertEqual(second.read_text(), 'old2')
            self.assertEqual(len(list(Path(tmp).iterdir())), 2)
            obj._publish_maps({first: 'new1', second: 'new2'})
            self.assertEqual(second.read_text(), 'new2')

    def test_disabled_constructor_does_not_unlink(self):
        storage = Mock()
        storage.get_dictionary_from_dconf_file_db.return_value = {}
        storage.get_drives.return_value = []
        with patch('gpoa_lib.frontend.cifs_applier.check_enabled', return_value=False), \
                patch('gpoa_lib.frontend.cifs_applier.jinja2.Environment'), \
                patch('gpoa_lib.frontend.cifs_applier.get_machine_name', return_value='host'), \
                patch.object(Path, 'unlink') as unlink:
            obj = cifs_applier(storage)
            obj.apply()
            unlink.assert_not_called()
