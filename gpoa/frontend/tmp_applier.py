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
from shutil import rmtree

from .applier_frontend import applier_frontend
from util.logging import slogm
from util.util import get_homedir

import logging

def remove_directory_contents(dirname):
    destpath = Path(dirname)
    if destpath.exists():
        for path in destpath.iterdir():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                rmtree(path)

class tmp_applier(applier_frontend):
    __registry_key = 'Software\\BaseALT\\Policies\\sys_tmp'
    __os_tmpdir = '/tmp'

    def __init__(self, storage):
        self.storage = storage
        self.clean_tmp_settings = self.storage.get_hklm_entry(self.__registry_key)

    def apply(self):
        '''
        Remove contents of /tmp directory
        '''
        if self.clean_tmp_settings == '1':
            remove_directory_contents(self.__os_tmpdir)


class tmp_applier_user(applier_frontend):
    __registry_key = 'Software\\BaseALT\\Policies\\user_tmp'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.clean_tmp_settings = self.storage.get_hkcu_entry(self.__registry_key)

    def user_context_apply(self):
        '''
        Clean user's tmp directory
        '''
        if self.clean_tmp_settings == '1':
            full_path = get_homedir(self.username) + '/tmp'
            remove_directory_contents(full_path)

    def admin_context_apply(self):
        '''
        Nothing to implement
        '''
        pass

