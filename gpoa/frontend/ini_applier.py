#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2022 BaseALT Ltd.
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

from pathlib import Path

from .appliers.file_cp import Files_cp
from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import log
from util.windows import expand_windows_var
from util.util import get_homedir


class file_applier(applier_frontend):
    __module_name = 'InifilesApplier'
    __module_experimental = True
    __module_enabled = False

    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.files_ini = self.storage.get_ini(self.sid)
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def run(self):
        pass


    def apply(self):
        if self.__module_enabled:
            print('D???')
            self.run()
        else:
            pass
            print('D???')

class file_applier_user(applier_frontend):
    __module_name = 'InifilesApplierUser'
    __module_experimental = True
    __module_enabled = False

    def __init__(self, storage, sid, username):
        self.sid = sid
        self.username = username
        self.storage = storage
        self.files = self.storage.get_ini(self.sid)
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        pass

    def admin_context_apply(self):
        if self.__module_enabled:
            print('D???')
            self.run()
        else:
            print('D???')

    def user_context_apply(self):
        pass
