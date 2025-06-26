#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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


from .appliers.ini_file import Ini_file
from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import log

class ini_applier(applier_frontend):
    __module_name = 'InifilesApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage):
        self.storage = storage
        self.inifiles_info = self.storage.get_ini()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def run(self):
        for inifile in self.inifiles_info:
            Ini_file(inifile)

    def apply(self):
        if self.__module_enabled:
            log('D171')
            self.run()
        else:
            log('D172')

class ini_applier_user(applier_frontend):
    __module_name = 'InifilesApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, username):
        self.username = username
        self.storage = storage
        self.inifiles_info = self.storage.get_ini()
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        for inifile in self.inifiles_info:
            Ini_file(inifile, self.username)

    def admin_context_apply(self):
        pass

    def user_context_apply(self):
        if self.__module_enabled:
            log('D173')
            self.run()
        else:
            log('D174')
