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

from .dynamic_attributes import DynamicAttributes

class GpoInfoDconf(DynamicAttributes):
    def __init__(self, gpo) -> None:
        self.display_name = None
        self.name = None
        self.version = None
        self.link = None
        self._fill_attributes(gpo)

    def _fill_attributes(self, gpo):
        try:
            self.display_name = gpo.display_name
        except:
            self.display_name = "Unknown"
        try:
            self.name = gpo.name
        except:
            self.name = "Unknown"
        try:
            self.version = gpo.version
        except:
            self.version = "Unknown"
        try:
            self.link = gpo.link
        except:
            self.link = "Unknown"
