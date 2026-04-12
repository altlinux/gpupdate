#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import os
import sys
import types
import importlib
import tempfile
import unittest.mock


def _load_change_journal():
    if 'frontend' not in sys.modules:
        frontend_pkg = types.ModuleType('frontend')
        frontend_pkg.__path__ = [os.path.join(os.getcwd(), 'frontend')]
        sys.modules['frontend'] = frontend_pkg
    return importlib.import_module('frontend.change_journal')


class ChangeJournalTestCase(unittest.TestCase):
    def test_changed_by_content_update(self):
        change_journal = _load_change_journal()
        change_journal.reset()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'a.txt')
            with open(path, 'w', encoding='utf-8') as file_obj:
                file_obj.write('first')
            change_journal.watch(path)
            with open(path, 'w', encoding='utf-8') as file_obj:
                file_obj.write('second')

            self.assertTrue(change_journal.query(path, mode='changed'))
            self.assertFalse(change_journal.query(path, mode='presence_changed'))

    def test_presence_changed_on_create_and_delete(self):
        change_journal = _load_change_journal()
        change_journal.reset()
        with tempfile.TemporaryDirectory() as tmpdir:
            created = os.path.join(tmpdir, 'create.txt')
            change_journal.watch(created)
            with open(created, 'w', encoding='utf-8') as file_obj:
                file_obj.write('x')

            self.assertTrue(change_journal.query(created, mode='presence_changed'))
            self.assertTrue(change_journal.query(created, mode='changed'))

            deleted = os.path.join(tmpdir, 'delete.txt')
            with open(deleted, 'w', encoding='utf-8') as file_obj:
                file_obj.write('x')
            change_journal.watch(deleted)
            os.unlink(deleted)

            self.assertTrue(change_journal.query(deleted, mode='presence_changed'))
            self.assertTrue(change_journal.query(deleted, mode='changed'))

    def test_unchanged_and_unwatched_paths(self):
        change_journal = _load_change_journal()
        change_journal.reset()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'same.txt')
            with open(path, 'w', encoding='utf-8') as file_obj:
                file_obj.write('same')
            change_journal.watch(path)

            self.assertFalse(change_journal.query(path, mode='changed'))
            self.assertFalse(change_journal.query(path, mode='presence_changed'))
            self.assertFalse(change_journal.query(os.path.join(tmpdir, 'unwatched.txt'), mode='changed'))

    def test_record_compatibility_for_manual_override(self):
        change_journal = _load_change_journal()
        change_journal.reset()

        change_journal.record_changed('/tmp/a')
        self.assertTrue(change_journal.query('/tmp/a', mode='changed'))
        self.assertFalse(change_journal.query('/tmp/a', mode='presence_changed'))

        change_journal.record_presence_changed('/tmp/b')
        self.assertTrue(change_journal.query('/tmp/b', mode='changed'))
        self.assertTrue(change_journal.query('/tmp/b', mode='presence_changed'))

    def test_query_reuses_current_snapshot_cache(self):
        change_journal = _load_change_journal()
        change_journal.reset()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'cache.txt')
            with open(path, 'w', encoding='utf-8') as file_obj:
                file_obj.write('content')
            change_journal.watch(path)

            with unittest.mock.patch.object(change_journal, '_sha256', wraps=change_journal._sha256) as hash_mock:
                self.assertFalse(change_journal.query(path, mode='changed'))
                self.assertFalse(change_journal.query(path, mode='changed'))
                self.assertEqual(hash_mock.call_count, 1)


if __name__ == '__main__':
    unittest.main()
