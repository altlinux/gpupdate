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
import tempfile
import os

from util.gpoa_ini_parsing import GpoaConfigObj


class TestIniSpecialChars(unittest.TestCase):
    '''
    Tests for allow_special_chars functionality in GpoaConfigObj.
    '''

    def test_quote_disabled_single_quote(self):
        '''
        When allow_special_chars=False (default), values with single quotes
        should be wrapped in double quotes.
        '''
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ini')
            config = GpoaConfigObj(filepath, allow_special_chars=False)
            config['section'] = {}
            config['section']['key'] = "123  'asas'"
            config.write()

            with open(filepath, 'r') as f:
                content = f.read()

            self.assertIn('"123  \'asas\'"', content)

    def test_quote_disabled_spaces(self):
        '''
        When allow_special_chars=False (default), values with leading/trailing
        spaces should be quoted.
        '''
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ini')
            config = GpoaConfigObj(filepath, allow_special_chars=False)
            config['section'] = {}
            config['section']['key'] = " spaces "
            config.write()

            with open(filepath, 'r') as f:
                content = f.read()

            self.assertIn('" spaces "', content)

    def test_quote_enabled_single_quote(self):
        '''
        When allow_special_chars=True, values with single quotes
        should NOT be quoted.
        '''
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ini')
            config = GpoaConfigObj(filepath, allow_special_chars=True)
            config['section'] = {}
            config['section']['key'] = "123  'asas'"
            config.write()

            with open(filepath, 'r') as f:
                content = f.read()

            self.assertIn("key = 123  'asas'", content)
            self.assertNotIn('"123  \'asas\'"', content)

    def test_quote_enabled_double_quote(self):
        '''
        When allow_special_chars=True, values with double quotes
        should NOT be quoted.
        '''
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ini')
            config = GpoaConfigObj(filepath, allow_special_chars=True)
            config['section'] = {}
            config['section']['key'] = 'test "value" end'
            config.write()

            with open(filepath, 'r') as f:
                content = f.read()

            self.assertIn('key = test "value" end', content)

    def test_quote_enabled_spaces(self):
        '''
        When allow_special_chars=True, values with leading/trailing
        spaces should NOT be quoted.
        '''
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ini')
            config = GpoaConfigObj(filepath, allow_special_chars=True)
            config['section'] = {}
            config['section']['key'] = " spaces "
            config.write()

            with open(filepath, 'r') as f:
                content = f.read()

            self.assertIn("key =  spaces ", content)
            self.assertNotIn('" spaces "', content)

    def test_quote_enabled_hash(self):
        '''
        When allow_special_chars=True, values with # should NOT be quoted.
        Note: This may cause the # to be interpreted as a comment.
        '''
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ini')
            config = GpoaConfigObj(filepath, allow_special_chars=True)
            config['section'] = {}
            config['section']['key'] = "value # comment"
            config.write()

            with open(filepath, 'r') as f:
                content = f.read()

            self.assertIn("key = value # comment", content)

    def test_backward_compatibility_default(self):
        '''
        By default (allow_special_chars not specified), behavior should be
        the same as allow_special_chars=False.
        '''
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.ini')
            config = GpoaConfigObj(filepath)
            config['section'] = {}
            config['section']['key'] = "test 'value'"
            config.write()

            with open(filepath, 'r') as f:
                content = f.read()

            self.assertIn('"test \'value\'"', content)


if __name__ == '__main__':
    unittest.main()