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

from util.rpm import (
      install_rpms
    , remove_rpms
)

class RPMTestCase(unittest.TestCase):
    @unittest.skip('test_install_rpm is not unit test')
    def test_install_rpm(self):
        test_package_names = ['tortoisehg', 'csync']
        install_rpms(test_package_names)

    @unittest.skip('test_remove_rpm is not unit test')
    def test_remove_rpm(self):
        test_package_names = ['tortoisehg', 'csync']
        remove_rpms(test_package_names)

