import itertools
import tempfile
import unittest
from pathlib import Path
from gpoa_lib.frontend.appliers.folder import remove_dir_tree


class FolderDeletionTest(unittest.TestCase):
    def test_flags_and_links(self):
        for files, folder, subfolders in itertools.product((False, True), repeat=3):
            with self.subTest(flags=(files, folder, subfolders)), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                external = base / 'external'
                external.mkdir()
                (external / 'secret').write_text('keep')
                tree = base / 'tree'
                tree.mkdir()
                (tree / 'link').symlink_to(external)
                (tree / 'broken').symlink_to(base / 'absent')
                (tree / 'file').touch()
                (tree / 'nested').mkdir()
                (tree / 'nested' / 'file').touch()
                remove_dir_tree(tree, files, folder, subfolders)
                self.assertEqual((external / 'secret').read_text(), 'keep')
                self.assertEqual((tree / 'file').exists(), not files)
                self.assertEqual((tree / 'nested' / 'file').exists(), not (files and subfolders))
                self.assertEqual(tree.exists(), not (files and folder and subfolders))

    def test_top_level_link_is_unlinked(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'target'
            target.mkdir()
            (target / 'keep').touch()
            link = Path(tmp) / 'link'
            link.symlink_to(target)
            remove_dir_tree(link, True, True, True)
            self.assertTrue((target / 'keep').exists())
            self.assertFalse(link.is_symlink())
