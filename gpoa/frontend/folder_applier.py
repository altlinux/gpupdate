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

from pathlib import Path

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from .appliers.folder import Folder
from util.logging import slogm

import logging

class folder_applier(applier_frontend):
    __module_name = 'FoldersApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.folders = self.storage.get_folders(self.sid)
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_enabled)

    def apply(self):
        if self.__module_enabled:
            logging.debug(slogm('Running Folder applier for machine'))
            for directory_obj in self.folders:
                fld = Folder(directory_obj)
                fld.action()
        else:
            logging.debug(slogm('Folder applier for machine will not be started'))

class folder_applier_user(applier_frontend):
    __module_name = 'FoldersApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.folders = self.storage.get_folders(self.sid)
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        for directory_obj in self.folders:
            fld = Folder(directory_obj, self.username)
            fld.act()

    def admin_context_apply(self):
        if self.__module_enabled:
            logging.debug(slogm('Running Folder applier for user in administrator context'))
            self.run()
        else:
            logging.debug(slogm('Folder applier for user in administrator context will not be started'))

    def user_context_apply(self):
        if self.__module_enabled:
            logging.debug(slogm('Running Folder applier for user in user context'))
            self.run()
        else:
            logging.debug(slogm('Folder applier for user administrator context will not be started'))

