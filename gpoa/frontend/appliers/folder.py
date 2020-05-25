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


from gpt.folders import (
      FileAction
    , action_letter2enum
)

def remove_dir_tree(path, delete_files=False, delete_folder=False, delete_sub_folders=False):
    for entry in path.iterdir():
        if entry.is_file():
            entry.unlink()
        if entry.is_dir():
            if delete_sub_folders:
                remove_dir_tree(entry,
                    delete_files,
                    delete_folder,
                    delete_sub_folders)

    if delete_folder:
        path.rmdir()

def str2bool(boolstr):
    if boolstr.lower in ['true', 'yes', '1']:
        return True
    return False

class Folder:
    def __init__(self, folder_object):
        self.folder_path = Path(folder_object.path)
        self.action = action_letter2enum(folder_object.action)
        self.delete_files = str2bool(folder_object.delete_files)
        self.delete_folder = str2bool(folder_object.delete_folder)
        self.delete_sub_folders = str2bool(folder_object.delete_sub_folders)

    def _create_action(self):
        self.folder_path.mkdir(parents=True, exist_ok=True)

    def _delete_action(self):
        remove_dir_tree(self.folder_path,
            self.delete_files,
            self.delete_folders,
            self.delete_sub_folders)

    def action(self):
        if self.action == FileAction.CREATE:
            self._create_action()
        if self.action == FileAction.DELETE:
            self._delete_action()
        if self.action == FileAction.REPLACE:
            self._delete_action()
            self._create_action()

