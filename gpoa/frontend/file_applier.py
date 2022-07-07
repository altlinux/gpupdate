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


class file_applier(applier_frontend):
    __module_name = 'FilesApplier'
    __module_experimental = True
    __module_enabled = False

    def __init__(self, storage, file_cache, sid):
        self.storage = storage
        self.sid = sid
        self.file_cache = file_cache
        self.files = self.storage.get_files(self.sid)
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_enabled)

    def run(self):
        dict_all_files = get_list_all_files(self.files, self.file_cache)


    # def apply(self):
        # if self.__module_enabled:
            # log('#########D107#########')
            # for file_obj in self.files:
                # check_from = expand_windows_var(file_obj.fromPath).replace('\\', '/')
                # check_target = expand_windows_var(file_obj.targetPath).replace('\\', '/')
        # else:
            # log('#############D108')

class file_applier_user(applier_frontend):
    __module_name = 'FilesApplierUser'
    __module_experimental = True
    __module_enabled = False

    def __init__(self, storage, file_cache, sid, username):
        self.storage = storage
        self.file_cache = file_cache
        self.sid = sid
        self.username = username
        self.files = self.storage.get_files(self.sid)
        self.ls_all_files = dict()
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        ls_files_cp = get_list_all_files(self.files, self.file_cache, self.username)

    # def admin_context_apply(self):
        # if self.__module_enabled:
            # log('###########D109')
            # self.run()
        # else:
            # log('############D110')

    # def user_context_apply(self):
        # if self.__module_enabled:
            # log('##############D111')
            # self.run()
        # else:
            # log('#############D112')
def get_list_all_files(files, file_cache, username = None):
    ls_files_cp = list()

    for file_obj in files:
        fromPath = expand_windows_var(file_obj.fromPath).replace('\\', '/')
        targetPath = expand_windows_var(file_obj.targetPath).replace('\\', '/')
        dict_files_cp = dict()
        dict_files_cp['targetPath'] = targetPath
        dict_files_cp['action'] = file_obj.action
        dict_files_cp['readOnly'] = file_obj.readOnly
        dict_files_cp['archive'] = file_obj.archive
        dict_files_cp['hidden'] = file_obj.hidden
        dict_files_cp['suppress'] = file_obj.suppress
        if fromPath[-1] != '*':
            try:
                file_cache.store(fromPath)
                dict_files_cp['fromPath'] = file_cache.get(fromPath)
            except Exception as exc:
                logdata = dict({fromPath: str(exc)})
                log('W13', logdata)
            ls_files_cp.append(Files_cp(dict_files_cp))
        else:
            ls_files = file_cache.get_ls_smbdir(fromPath[:-1])
            ls_from_paths = [fromPath[:-1] + file_s for file_s in ls_files]
            for from_path in ls_from_paths:
                try:
                    file_cache.store(from_path)
                    dict_files_cp['fromPath'] = file_cache.get(from_path)
                except Exception as exc:
                    logdata = dict({from_path: str(exc)})
                    log('W13', logdata)
                ls_files_cp.append(Files_cp(dict_files_cp))

    return ls_files_cp

def cp_all_files(ls_files_cp):
    ls_files_cp
