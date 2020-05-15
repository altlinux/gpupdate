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

from .applier_frontend import applier_frontend
from .appliers.folder import Folder
from util.logging import slogm

import logging

class folder_applier(applier_frontend):
    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.folders = self.storage.get_folders(self.sid)

    def apply(self):
        for directory_obj in self.folders:
            fld = Folder(directory_obj)
            fld.action()

class folder_applier_user(applier_frontend):
    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.folders = self.storage.get_folders(self.sid)

    def admin_context_apply(self):
        for directory_obj in self.folders:
            fld = Folder(directory_obj)
            fld.action()

    def user_context_apply(self):
        print('folder:user:user')
        for directory_obj in self.folders:
            fld = Folder(directory_obj)
            fld.action()

