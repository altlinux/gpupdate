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

from .appliers.ini_file import Ini_file
from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import log
from util.windows import expand_windows_var
from util.util import get_homedir


class ini_applier(applier_frontend):
    __module_name = 'InifilesApplier'
    __module_experimental = True
    __module_enabled = False

    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.inifiles_info = self.storage.get_ini(self.sid)
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def run(self):
        list_all_inifiles = get_list_all_inifiles(self.inifiles_info)
        for inifile in list_all_inifiles:
            inifile.act()

    def apply(self):
        if self.__module_enabled:
            print('D???start file_applier')
            self.run()
        else:
            print('D???do not use  file_applier')

class ini_applier_user(applier_frontend):
    __module_name = 'InifilesApplierUser'
    __module_experimental = True
    __module_enabled = False

    def __init__(self, storage, sid, username):
        self.sid = sid
        self.username = username
        self.storage = storage
        self.inifiles_info = self.storage.get_ini(self.sid)
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        list_all_inifiles = get_list_all_inifiles(self.inifiles_info, self.username)
        for inifile in list_all_inifiles:
            inifile.act()

    def admin_context_apply(self):
        if self.__module_enabled:
            print('D???start file_applier_user')
            self.run()
        else:
            print('D???do not use file_applier_user')

    def user_context_apply(self):
        pass

def get_list_all_inifiles(inifiles_info, username = None):
    '''
    Forming a list of ini_files objects
    '''
    ls_ini_files = list()

    for ini_obj in inifiles_info:
        path = expand_windows_var(ini_obj.path, username).replace('\\', '/')
        dict_ini_file = dict()
        dict_ini_file['path'] = check_path(path, username)
        if not dict_ini_file['path']:
            continue
        dict_ini_file['action'] = ini_obj.action
        dict_ini_file['section'] = ini_obj.section
        dict_ini_file['property'] = ini_obj.property
        dict_ini_file['value'] = ini_obj.value
        ls_ini_files.append(Ini_file(dict_ini_file))

    return ls_ini_files

def check_path(path_to_check, username = None):
    '''
    Function for checking the right path for Inifile
    '''
    checking = Path(path_to_check)
    if checking.exists():
        return checking
    #Check for path directory without '/nameIni' suffix
    elif (len(path_to_check.split('/')) > 2
          and Path(path_to_check.replace(path_to_check.split('/')[-1], '')).is_dir()):
        return checking
    elif username:
        target_path = Path(get_homedir(username))
        res = target_path.joinpath(path_to_check
                                    if path_to_check[0] != '/'
                                    else path_to_check[1:])
        return check_path(res)
    else:
        return False
