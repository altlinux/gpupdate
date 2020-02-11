#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
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
import unittest.mock

import os

import util.paths


class GptShortcutsTestCase(unittest.TestCase):
    @unittest.mock.patch('util.paths.cache_dir')
    def test_shortcut_reader(self, cdir_mock):
        '''
        Test functionality to read objects from Shortcuts.xml
        '''
        cdir_mock.return_value = '/var/cache/gpupdate'

        import gpt.shortcuts
        testdata_path = '{}/test/gpt/data/Shortcuts.xml'.format(os.getcwd())
        sc = gpt.shortcuts.read_shortcuts(testdata_path)
        print(sc[0].to_json())

