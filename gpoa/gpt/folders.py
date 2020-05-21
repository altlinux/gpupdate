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


from enum import Enum


from util.xml import get_xml_root


class FileAction(Enum):
    CREATE = 'C'
    REPLACE = 'R'
    UPDATE = 'U'
    DELETE = 'D'


def action_letter2enum(letter):
    if letter in ['C', 'R', 'U', 'D']:
        if letter == 'C': return FileAction.CREATE
        if letter == 'R': return FileAction.REPLACE
        if letter == 'U': return FileAction.UPDATE
        if letter == 'D': return FileAction.DELETE

    return FileAction.CREATE


def action_enum2letter(enumitem):
    return enumitem.value


def folder_int2bool(val):
    value = val

    if type(value) == str:
        value = int(value)

    if value == 0:
        return True

    return False


def read_folders(folders_file):
    folders = list()

    for fld in get_xml_root(folders_file):
        props = fld.find('Properties')
        fld_obj = folderentry(props.get('path'))
        fld_obj.set_action(action_letter2enum(props.get('action')))
        fld_obj.set_delete_folder(folder_int2bool(props.get('deleteFolder')))
        fld_obj.set_delete_sub_folder(folder_int2bool(props.get('deleteSubFolders')))
        fld_obj.set_delete_files(folder_int2bool(props.get('deleteFiles')))

        folders.append(fld_obj)

    return folders

def merge_folders(storage, sid, folder_objects, policy_name):
    for folder in folder_objects:
        storage.add_folder(sid, folder, policy_name)


class folderentry:
    def __init__(self, path):
        self.path = path
        self.action = FileAction.CREATE
        self.delete_folder = False
        self.delete_sub_folder = False
        self.delete_files = False

    def set_action(self, action):
        self.action = action

    def set_delete_folder(self, del_bool):
        self.delete_folder = del_bool

    def set_delete_sub_folder(self, del_bool):
        self.delete_sub_folder = del_bool

    def set_delete_files(self, del_bool):
        self.delete_files = del_bool

