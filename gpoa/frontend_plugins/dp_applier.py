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

from gpoa.plugin.plugin import plugin
from util.logging import log



class DPApplier(plugin):
    """
    Display Policy Applier - handles loading of display policy keys
    from registry (machine/user) and user preferences.
    """

    __registry_path  = 'Software/BaseALT/Policies/DisplayManager'

    def __init__(self, dict_dconf_db, username = None):
        super().__init__(dict_dconf_db, username)
        self.config = self.get_dict_registry(self.__registry_path)




    def run(self):
        print('self.config', self.config)

def create_applier(dict_dconf_db, username = None) -> DPApplier:
    """Factory function to create DPApplier instance"""
    return DPApplier(dict_dconf_db, username)
