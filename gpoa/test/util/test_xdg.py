#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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

from util.xdg import (
    xdg_get_desktop_user
)

class XDGTestCase(unittest.TestCase):
    def test_get_desktop_dir(self):
        print('Machine desktop:')
        print(xdg_get_desktop_user(None))
        print('Users desktop:')
        print(xdg_get_desktop_user('nir'))

