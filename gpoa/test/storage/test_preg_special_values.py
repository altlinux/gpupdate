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


class StorageTestCase(unittest.TestCase):
    preg_xml_path = '{}/test/storage/data/Registry.pol.xml'.format(os.getcwd())
    reg_name = 'registry'
    # Run destructive storage tests in current directory
    reg_path = '{}/test/tmp'.format(os.getcwd())

    @unittest.mock.patch('util.paths.cache_dir')
    def test_add_hklm_entry(self, cdir_mock):
        test_sid = None

        from util.preg import merge_polfile

        merge_polfile(self.preg_xml_path, test_sid, self.reg_name, self.reg_path)

    @unittest.mock.patch('util.paths.cache_dir')
    def test_add_hkcu_entry(self, cdir_mock):
        test_sid = 'test_sid'

        from util.preg import merge_polfile

        merge_polfile(self.preg_xml_path, test_sid, self.reg_name, self.reg_path)

