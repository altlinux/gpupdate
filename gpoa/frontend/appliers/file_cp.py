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

class Files_cp:
    def __init__(self, arg_dict):
        self.fromPath = (arg_dict['fromPath']
                        if arg_dict['fromPath'] else None)
        self.targetPath = arg_dict['targetPath']
        self.action = action_letter2enum(arg_dict['action'])
        self.readOnly = str2bool(arg_dict['readOnly'])
        self.archive = str2bool(arg_dict['archive'])
        self.hidden = str2bool(arg_dict['hidden'])
        self.suppress = (str2bool(arg_dict['suppress'])
                        if arg_dict['suppress'] else None)
        self.username = arg_dict['username']

    def get_target_file(self):
        try:
            if self.fromPath and self.targetPath.is_dir():
                if self.hidden:
                    return self.targetPath.joinpath('.' + self.fromPath.name)
                else:
                    return (self.targetPath.joinpath(self.fromPath.name))

            else:
                if not self.hidden:
                    return self.targetPath
                else:
                    return self.targetPath.parent.joinpath('.' + self.targetPath.name)

        except Exception as exc:
            logdata = dict({'exc': exc})
            log('D163', logdata)

    def set_read_only(self, targetFile):
        if  self.readOnly:
            shutil.os.chmod(targetFile, int('444', base = 8))
        else:
            shutil.os.chmod(targetFile, int('664', base = 8))

    def _create_action(self):
        try:
            targetFile = self.get_target_file()
            if not targetFile.exists():
                targetFile.write_bytes(self.fromPath.read_bytes())
                if self.username:
                    shutil.chown(targetFile, self.username)
                self.set_read_only(targetFile)
        except Exception as exc:
            logdata = dict()
            logdata['exc'] = exc
            logdata['fromPath'] = self.fromPath
            logdata['targetPath'] = self.targetPath
            log('D164', logdata)

    def _delete_action(self):
        try:
            targetFile = self.get_target_file()
            if targetFile.exists():
                targetFile.unlink()
        except Exception as exc:
            logdata = dict()
            logdata['exc'] = exc
            logdata['targetPath'] = self.targetPath
            log('D165', logdata)

    def _update_action(self):
        try:
            targetFile = self.get_target_file()
            targetFile.write_bytes(self.fromPath.read_bytes())
            if self.username:
                shutil.chown(self.targetPath, self.username)
            self.set_read_only(targetFile, self.readOnly)
        except Exception as exc:
            logdata = dict()
            logdata['exc'] = exc
            logdata['fromPath'] = self.fromPath
            logdata['targetPath'] = self.targetPath
            log('D166', logdata)

    def act(self):
        if self.action == FileAction.CREATE:
            self._create_action()
        if self.action == FileAction.UPDATE:
            self._create_action()
        if self.action == FileAction.DELETE:
            self._delete_action()
        if self.action == FileAction.REPLACE:
            self._delete_action()
            self._create_action()

