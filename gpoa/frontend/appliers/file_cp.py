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
import fnmatch

class Files_cp:
    def __init__(self, file_obj, file_cache ,username=None):
        self.file_cache = file_cache
        targetPath = expand_windows_var(file_obj.targetPath, username).replace('\\', '/')
        self.targetPath = check_target_path(targetPath, username)
        if not self.targetPath:
            return
        self.fromPath = (expand_windows_var(file_obj.fromPath, username).replace('\\', '/')
                        if file_obj.fromPath else None)
        self.action = action_letter2enum(file_obj.action)
        self.readOnly = str2bool(file_obj.readOnly)
        self.archive = str2bool(file_obj.archive)
        self.hidden = str2bool(file_obj.hidden)
        self.suppress = str2bool(file_obj.suppress)
        self.username = username
        if self.fromPath:
            self.fromPathFiles = self.get_list_files()
        self.act()

    def get_target_file(self, targetPath:Path, fromFile:Path) -> Path:
        try:
            if fromFile:
                check = set(str(targetPath).split('/')) & set(str(fromFile).split('/'))
                if len(check) < 2 :
                    targetPath.mkdir(parents = True, exist_ok = True)
                else:
                    targetPath.parent.mkdir(parents = True, exist_ok = True)
                    targetPath = targetPath.parent
                if self.hidden:
                    return targetPath.joinpath('.' + fromFile.name)
                else:
                    return targetPath.joinpath(fromFile.name)

            else:
                if not self.hidden:
                    return targetPath
                else:
                    return targetPath.parent.joinpath('.' + targetPath.name)

        except Exception as exc:
            logdata = dict({'exc': exc})
            log('D163', logdata)

    def set_read_only(self, targetFile):
        if  self.readOnly:
            shutil.os.chmod(targetFile, int('444', base = 8))
        else:
            shutil.os.chmod(targetFile, int('664', base = 8))

    def _create_action(self):
        for fromFile in self.fromPathFiles:
            try:
                targetFile = self.get_target_file(self.targetPath, fromFile)
                if not targetFile.exists():
                    targetFile.write_bytes(fromFile.read_bytes())
                    if self.username:
                        shutil.chown(targetFile, self.username)
                    self.set_read_only(targetFile)
            except Exception as exc:
                logdata = dict()
                logdata['exc'] = exc
                logdata['fromPath'] = fromFile
                logdata['targetPath'] = self.targetPath
                logdata['targetFile'] = targetFile
                log('D164', logdata)

    def _delete_action(self):
        targetPathSplit = str(self.targetPath).split('/')
        pattern = self.is_pattern(targetPathSplit)
        list_target = list()
        tPath = None
        if not pattern:
            list_target.append(self.targetPath)
        else:
            tPath = Path('/'.join(targetPathSplit[:-1]))
            files = [str(x).split('/')[-1] for x in tPath.iterdir() if x.is_file()]
            list_target = fnmatch.filter(files, targetPathSplit[-1])

        for targetFile in list_target:
            if tPath:
                targetFile = tPath.joinpath(targetFile)
            try:
                if targetFile.exists():
                    targetFile.unlink()
            except Exception as exc:
                logdata = dict()
                logdata['exc'] = exc
                logdata['targetPath'] = self.targetPath
                logdata['targetFile'] = targetFile
                log('D165', logdata)

    def _update_action(self):
        for fromPath in self.fromPathFiles:
            targetFile = self.get_target_file(self.targetPath, fromPath)
            try:
                targetFile.write_bytes(fromPath.read_bytes())
                if self.username:
                    shutil.chown(self.targetPath, self.username)
                self.set_read_only(targetFile)
            except Exception as exc:
                logdata = dict()
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
    def is_pattern(self, path_split):
        if path_split[-1].find('*') != -1 or path_split[-1].find('?') != -1:
            return True
        else:
            return False

    def get_list_files(self):
        ls_all_files = list()
        logdata = dict()
        logdata['targetPath'] = self.targetPath
        fromPathSplit = self.fromPath.split('/')
        pattern = self.is_pattern(fromPathSplit)
        if self.fromPath and not pattern:
            try:
                self.file_cache.store(self.fromPath)
                fromPath = Path(self.file_cache.get(self.fromPath))
                ls_all_files.append(fromPath)
            except NotUNCPathError as exc:
                fromPath = Path(self.fromPath)
                if fromPath.exists():
                    ls_all_files.append(fromPath)
            except Exception as exc:
                logdata['fromPath'] = self.fromPath
                logdata['exc'] = exc
                log('W13', logdata)
        elif self.fromPath and len(fromPathSplit) > 2:
            exact_path = '/'.join(fromPathSplit[:-1])
            ls_files = self.file_cache.get_ls_smbdir(exact_path)
            filtered_ls_files = fnmatch.filter(ls_files, fromPathSplit[-1])
            if filtered_ls_files:
                ls_from_paths = [exact_path +'/'+ file_s for file_s in filtered_ls_files]
                for from_path in ls_from_paths:
                    try:
                        self.file_cache.store(from_path)
                        fromPath = Path(self.file_cache.get(from_path))
                        ls_all_files.append(fromPath)
                    except Exception as exc:
                        logdata['fromPath'] = self.fromPath
                        logdata['exc'] = exc
                        log('W13', logdata)
            else:
                try:
                    fromLocalPath = Path(exact_path)
                    if fromLocalPath.is_dir():
                        ls = [fromFile for fromFile in fromLocalPath.iterdir() if fromFile.is_file()]
                        for fromPath in ls:
                            ls_all_files.append(fromPath)
                except Exception as exc:
                    logdata['fromPath'] = self.fromPath
                    logdata['exc'] = exc
                    log('W13', logdata)
        else:
            fromPath = Path(self.fromPath) if self.fromPath else None
            ls_all_files.append(fromPath)
        return ls_all_files

def check_target_path(path_to_check, username = None):
    '''
    Function for checking the correctness of the path
    '''
    checking = Path(path_to_check)
    if checking.is_dir():
        if username and path_to_check == '/':
            return Path(get_homedir(username))
        return checking
    #Check for path directory without '/something' suffix
    elif (len(path_to_check.split('/')) > 2
          and Path(path_to_check.replace(path_to_check.split('/')[-1], '')).is_dir()):
        return checking
    elif username:
        target_path = Path(get_homedir(username))
        res = target_path.joinpath(path_to_check
                                    if path_to_check[0] != '/'
                                    else path_to_check[1:])
        return res
    else:
        return False
