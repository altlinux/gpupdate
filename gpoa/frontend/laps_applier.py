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

from .applier_frontend import (
      applier_frontend
    , check_enabled
    , check_windows_mapping_enabled
)


class laps_applier(applier_frontend):
    __module_name = 'LapsApplier'
    __module_experimental = True
    __module_enabled = False
    __all_win = 'Software/Microsoft/Windows/CurrentVersion/Policies/LAPS'
    __registry_branch = 'Software/BaseALT/Policies/Laps'


    def __init__(self, storage):
        self.storage = storage
        deny_all_win = None
        if check_windows_mapping_enabled(self.storage):
            deny_all_win = storage.filter_hklm_entries(self.__all_win)

        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def apply(self):
        if self.__module_enabled:
            print('Dlog')
        else:
            print('Dlog')
