import tempfile
import unittest
from pathlib import Path
from gpoa_lib.storage.gpp_state import cleanup_file, cleanup_folder


class HiddenCleanupTest(unittest.TestCase):
    def test_visible_siblings_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name in ('team', '.team'):
                (base / name).mkdir()
                (base / name / 'file').touch()
            cleanup_folder({'path': str(base / 'team'), 'hidden_folder': True,
                            'delete_files': True, 'delete_folder': True, 'delete_sub_folders': True})
            self.assertTrue((base / 'team' / 'file').exists())
            self.assertFalse((base / '.team').exists())
            for name in ('file', '.file'):
                (base / name).touch()
            cleanup_file({'targetPath': str(base / 'file'), 'hidden': True})
            self.assertTrue((base / 'file').exists())
            self.assertFalse((base / '.file').exists())
