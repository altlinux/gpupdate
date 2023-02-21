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


from gpt.folders import (
      FileAction
    , action_letter2enum
)
from .folder import str2bool
from util.logging import log
import shutil
from pathlib import Path
from util.windows import expand_windows_var
from util.util import get_homedir
from util.exceptions import NotUNCPathError
from util.paths import UNCPath
import fnmatch

class Files_cp:
    def __init__(self, file_obj, file_cache, exe_check, username=None):
        self.file_cache = file_cache
        self.exe_check = exe_check
        targetPath = expand_windows_var(file_obj.targetPath, username).replace('\\', '/')
        self.targetPath = check_target_path(targetPath, username)
        if not self.targetPath:
            return
        self.fromPath = (expand_windows_var(file_obj.fromPath, username).replace('\\', '/')
                        if file_obj.fromPath else None)
        self.isTargetPathDirectory = False
        self.action = action_letter2enum(file_obj.action)
        self.readOnly = str2bool(file_obj.readOnly)
        self.archive = str2bool(file_obj.archive)
        self.hidden = str2bool(file_obj.hidden)
        self.suppress = str2bool(file_obj.suppress)
        self.username = username
        self.fromPathFiles = list()
        if self.fromPath:
            if targetPath[-1] == '/' or self.is_pattern(Path(self.fromPath).name):
                self.isTargetPathDirectory = True
            self.get_list_files()
        self.act()

    def get_target_file(self, targetPath:Path, fromFile:str) -> Path:
        try:
            if fromFile:
                fromFileName = Path(fromFile).name
                if self.isTargetPathDirectory:
                    targetPath.mkdir(parents = True, exist_ok = True)
                else:
                    targetPath.parent.mkdir(parents = True, exist_ok = True)
                    targetPath = targetPath.parent
                    fromFileName = self.targetPath.name
                if self.hidden:
                    return targetPath.joinpath('.' + fromFileName)
                else:
                    return targetPath.joinpath(fromFileName)

            else:
                if not self.hidden:
                    return targetPath
                else:
                    return targetPath.parent.joinpath('.' + targetPath.name)
        except Exception as exc:
            logdata = dict()
            logdata['targetPath'] = targetPath
            logdata['fromFile'] = fromFile
            logdata['exc'] = exc
            log('D163', logdata)

        return None

    def copy_target_file(self, targetFile:Path, fromFile:str):
        try:
            uri_path = UNCPath(fromFile)
            self.file_cache.store(fromFile, targetFile)
        except NotUNCPathError as exc:
            fromFilePath = Path(fromFile)
            if fromFilePath.exists():
                targetFile.write_bytes(fromFilePath.read_bytes())
        except Exception as exc:
            logdata = dict()
            logdata['targetFile'] = targetFile
            logdata['fromFile'] = fromFile
            logdata['exc'] = exc
            log('W15', logdata)

    def set_exe_file(self, targetFile, fromFile):
        if Path(fromFile).suffix in self.exe_check.get_list_markers():
            targetPath = str(targetFile.parent)
            if targetPath or targetPath + '/' in self.exe_check.get_list_paths():
                if self.readOnly:
                    shutil.os.chmod(targetFile, 0o555)
                else:
                    shutil.os.chmod(targetFile, 0o775)
        else:
            if self.readOnly:
                shutil.os.chmod(targetFile, 0o444)
            else:
                shutil.os.chmod(targetFile, 0o664)

    def _create_action(self):
        logdata = dict()
        for fromFile in self.fromPathFiles:
            targetFile = None

            try:
                targetFile = self.get_target_file(self.targetPath, fromFile)
                if targetFile and not targetFile.exists():
                    self.copy_target_file(targetFile, fromFile)
                    if self.username:
                        shutil.chown(targetFile, self.username)
                    self.set_exe_file(targetFile, fromFile)
                    logdata['File'] = targetFile
                    log('D191', logdata)
            except Exception as exc:
                logdata['exc'] = exc
                logdata['fromPath'] = fromFile
                logdata['targetPath'] = self.targetPath
                logdata['targetFile'] = targetFile
                log('D164', logdata)

    def _delete_action(self):
        list_target = [self.targetPath.name]
        if self.is_pattern(self.targetPath.name) and self.targetPath.parent.exists() and self.targetPath.parent.is_dir():
            list_target = fnmatch.filter([str(x.name) for x in self.targetPath.parent.iterdir() if x.is_file()], self.targetPath.name)
        logdata = dict()
        for targetFile in list_target:
            targetFile = self.targetPath.parent.joinpath(targetFile)
            try:
                if targetFile.exists():
                    targetFile.unlink()
                    logdata['File'] = targetFile
                    log('D192', logdata)

            except Exception as exc:
                logdata['exc'] = exc
                logdata['targetPath'] = self.targetPath
                logdata['targetFile'] = targetFile
                log('D165', logdata)

    def _update_action(self):
        logdata = dict()
        for fromFile in self.fromPathFiles:
            targetFile = self.get_target_file(self.targetPath, fromFile)
            try:
                self.copy_target_file(targetFile, fromFile)
                if self.username:
                    shutil.chown(self.targetPath, self.username)
                self.set_exe_file(targetFile, fromFile)
                logdata['File'] = targetFile
                log('D192', logdata)
            except Exception as exc:
                logdata['exc'] = exc
                logdata['fromPath'] = self.fromPath
                logdata['targetPath'] = self.targetPath
                logdata['targetFile'] = targetFile
                log('D166', logdata)

    def act(self):
        if self.action == FileAction.CREATE:
            self._create_action()
        if self.action == FileAction.UPDATE:
            self._update_action()
        if self.action == FileAction.DELETE:
            self._delete_action()
        if self.action == FileAction.REPLACE:
            self._delete_action()
            self._create_action()

    def is_pattern(self, name):
        if name.find('*') != -1 or name.find('?') != -1:
            return True
        else:
            return False

    def get_list_files(self):
        logdata = dict()
        logdata['targetPath'] = str(self.targetPath)
        fromFilePath = Path(self.fromPath)
        if not self.is_pattern(fromFilePath.name):
            self.fromPathFiles.append(self.fromPath)
        else:
            fromPathDir = self.fromPath[:self.fromPath.rfind('/')]

            try:
                uri_path = UNCPath(fromPathDir)
                ls_files = self.file_cache.get_ls_smbdir(fromPathDir)
                if ls_files:
                    filtered_ls_files = fnmatch.filter(ls_files, fromFilePath.name)
                    if filtered_ls_files:
                        self.fromPathFiles = [fromPathDir + '/' + file_s for file_s in filtered_ls_files]
            except NotUNCPathError as exc:
                try:
                    exact_path = Path(fromPathDir)
                    if exact_path.is_dir():
                        self.fromPathFiles = [str(fromFile) for fromFile in exact_path.iterdir() if fromFile.is_file()]
                except Exception as exc:
                    logdata['fromPath'] = self.fromPath
                    logdata['exc'] = exc
                    log('W3316', logdata)
            except Exception as exc:
                logdata['fromPath'] = self.fromPath
                logdata['exc'] = exc
                log('W3317', logdata)

def check_target_path(path_to_check, username = None):
    '''
    Function for checking the correctness of the path
    '''
    if not path_to_check:
        return None

    checking = Path(path_to_check)
    rootpath = Path('/')
    if username:
        rootpath = Path(get_homedir(username))

    return rootpath.joinpath(checking)

class Execution_check():

    __etension_marker_key_name = 'ExtensionMarker'
    __marker_usage_path_key_name = 'MarkerUsagePath'
    __hklm_branch = 'Software\\BaseALT\\Policies\\GroupPolicies\\Files'

    def __init__(self, storage):
        etension_marker_branch = '{}\\{}%'.format(self.__hklm_branch, self.__etension_marker_key_name)
        marker_usage_path_branch = '{}\\{}%'.format(self.__hklm_branch, self.__marker_usage_path_key_name)
        self.etension_marker = storage.filter_hklm_entries(etension_marker_branch)
        self.marker_usage_path = storage.filter_hklm_entries(marker_usage_path_branch)
        self.list_paths = list()
        self.list_markers = list()
        for marker in self.etension_marker:
            self.list_markers.append(marker.data)
        for usage_path in self.marker_usage_path:
            self.list_paths.append(usage_path.data)

    def get_list_paths(self):
        return self.list_paths

    def get_list_markers(self):
        return self.list_markers
