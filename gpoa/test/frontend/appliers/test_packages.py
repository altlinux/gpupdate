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

from frontend.appliers.rpm import rpm

class PackageTestCase(unittest.TestCase):
    '''
    Semi-integrational tests for packages installation/removing
    '''
    def test_package_not_exist(self):
        packages_for_install = 'dummy1 dummy2'
        packages_for_remove = 'dummy3'

        test_rpm = rpm(packages_for_install, packages_for_remove)
        test_rpm.apply()

    def test_install_remove_same_package(self):
        packages_for_install = 'gotop'
        packages_for_remove = 'gotop'

        test_rpm = rpm(packages_for_install, packages_for_remove)
        test_rpm.apply()
