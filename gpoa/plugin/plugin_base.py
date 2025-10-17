#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2025 BaseALT Ltd.
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

from abc import abstractmethod
from gpoa.plugin.plugin import plugin

class FrontendPlugin(plugin):
    """
    Base class for frontend plugins with simplified logging support.
    """

    def __init__(self, dict_dconf_db={}, username=None, fs_file_cache=None):
        super().__init__(dict_dconf_db, username, fs_file_cache)

    @abstractmethod
    def run(self):
        """
        Abstract method that must be implemented by concrete plugins.
        This method should contain the main plugin execution logic.
        """
        pass








