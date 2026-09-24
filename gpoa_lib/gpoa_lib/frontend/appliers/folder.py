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
import os
import stat


from ...util.arguments import (
      FileAction
    , action_letter2enum
)
from ...util.windows_vars import expand_windows_var
from ...util.util import get_homedir

def remove_dir_tree(path, delete_files=False, delete_folder=False, delete_sub_folders=False):
    path = Path(os.path.abspath(path))
    if path == Path('/'):
        raise ValueError('Refusing to remove the filesystem root')
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parent.parts[1:]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=parent)
            os.close(parent)
            parent = child
        return _remove_at(parent, path.name, path, delete_files,
                          delete_folder, delete_sub_folders, top=True)
    finally:
        os.close(parent)


def _remove_at(parent, name, path, files, folder, subfolders, top=False):
    info = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode):
        if (folder if top else files):
            os.unlink(name, dir_fd=parent)
            return []
        return [path]
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        if not os.path.samestat(info, os.fstat(fd)):
            raise OSError('Directory changed during deletion')
        remaining = []
        for entry in os.listdir(fd):
            entry_info = os.stat(entry, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(entry_info.st_mode):
                if subfolders:
                    remaining.extend(_remove_at(fd, entry, path / entry,
                                                files, folder, subfolders))
                else:
                    remaining.append(path / entry)
            elif files:
                os.unlink(entry, dir_fd=fd)
            else:
                remaining.append(path / entry)
        if folder and not remaining:
            if not os.path.samestat(os.fstat(fd), os.stat(name, dir_fd=parent, follow_symlinks=False)):
                raise OSError('Directory changed during deletion')
            os.rmdir(name, dir_fd=parent)
            return []
        return remaining or [path]
    finally:
        os.close(fd)

def str2bool(boolstr):
    if isinstance(boolstr, bool):
        return boolstr
    elif isinstance(boolstr, int):
        return bool(boolstr)
    elif boolstr and boolstr.lower() in ['true', 'yes', '1']:
        return True
    return False


class Folder:
    def __init__(self, folder_object, username=None):
        folder_path = expand_windows_var(folder_object.path, username).replace('\\', '/').replace('//', '/')
        if username:
            folder_path = folder_path.replace(get_homedir(username), '')
            self.folder_path = Path(get_homedir(username)).joinpath(folder_path if folder_path [0] != '/' else folder_path [1:])
        else:
            self.folder_path = Path(folder_path)
        self.action = action_letter2enum(folder_object.action)
        self.delete_files = str2bool(folder_object.delete_files)
        self.delete_folder = str2bool(folder_object.delete_folder)
        self.delete_sub_folders = str2bool(folder_object.delete_sub_folders)
        self.hidden_folder = str2bool(folder_object.hidden_folder)

    def _create_action(self):
        self.folder_path.mkdir(parents=True, exist_ok=True)

    def _delete_action(self):
        if self.folder_path.exists():
            if self.action == FileAction.REPLACE:
                self.delete_files = True
                self.delete_sub_folders = True
                self.delete_folder = True
            remove_dir_tree(self.folder_path,
                self.delete_files,
                self.delete_folder,
                self.delete_sub_folders)


    def act(self):
        if self.hidden_folder == True and str(self.folder_path.name)[0] != '.':
            path_components = [*self.folder_path.parts]
            path_components[-1] = '.' + path_components[-1]
            new_folder_path = Path(*path_components)
            self.folder_path = new_folder_path
        if self.action == FileAction.CREATE:
            self._create_action()
        if self.action == FileAction.UPDATE:
            self._create_action()
        if self.action == FileAction.DELETE:
            self._delete_action()
        if self.action == FileAction.REPLACE:
            self._delete_action()
            self._create_action()
