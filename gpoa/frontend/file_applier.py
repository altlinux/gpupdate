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


from util.logging import log

from .applier_frontend import applier_frontend, check_enabled
from .appliers.file_cp import Execution_check, Files_cp


class file_applier(applier_frontend):
    __module_name = 'FilesApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, file_cache):
        self.storage = storage
        self.exe_check = Execution_check(storage)
        self.file_cache = file_cache
        self.files = self.storage.get_files()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def run(self):
        for file in self.files:
            Files_cp(file, self.file_cache, self.exe_check)

    def apply(self):
        if self.__module_enabled:
            log('D167')
            self.run()
        else:
            log('D168')

class file_applier_user(applier_frontend):
    __module_name = 'FilesApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, file_cache, username):
        self.storage = storage
        self.file_cache = file_cache
        self.username = username
        self.exe_check = Execution_check(storage)
        self.files = self.storage.get_files()
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        for file in self.files:
            Files_cp(file, self.file_cache, self.exe_check, self.username)

    def admin_context_apply(self):
        if self.__module_enabled:
            log('D169')
            self.run()
        else:
            log('D170')

    def user_context_apply(self):
        pass
