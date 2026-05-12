#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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

from ..util.xml import get_xml_root
from ..util.util import utc_to_local
from ..util.gpp_lifecycle import generate_folder_uid

from .dynamic_attributes import DynamicAttributes
from .filter import parse_filters


def action_enum2letter(enumitem):
    return enumitem.value


def folder_int2bool(val):
    value = val

    if type(value) == str:
        value = int(value)

    if value == 1:
        return True

    return False


def read_folders(folders_file):
    folders = []

    for fld in get_xml_root(folders_file):
        props = fld.find('Properties')
        path = props.get('path')
        action = props.get('action', default='C')
        fld_obj = folderentry(path, action)
        fld_obj.set_delete_folder(folder_int2bool(props.get('deleteFolder', default=1)))
        fld_obj.set_delete_sub_folders(folder_int2bool(props.get('deleteSubFolders', default=1)))
        fld_obj.set_delete_files(folder_int2bool(props.get('deleteFiles', default=1)))
        fld_obj.set_hidden_folder(folder_int2bool(props.get('hidden', default=0)))
        fld_obj.set_disabled(fld.get('disabled') == '1')

        # Lifecycle attributes
        fld_obj.set_uid(fld.get('uid'))
        fld_obj.set_remove_policy(fld.get('removePolicy') == '1')
        fld_obj.set_bypass_errors(fld.get('bypassErrors') == '1')
        fld_obj.set_changed(fld.get('changed'))

        # Check for FilterRunOnce
        filters = fld.find('Filters')
        if filters is not None:
            run_once = filters.find('FilterRunOnce')
            fld_obj.set_apply_once(run_once is not None)
        else:
            fld_obj.set_apply_once(False)

        # Parse and add filters
        filters = parse_filters(fld)
        if filters:
            fld_obj.filters = filters

        folders.append(fld_obj)

    return folders

def merge_folders(storage, folder_objects, policy_name, policy_guid=None):
    for folder in folder_objects:
        storage.add_folder(folder, policy_name, policy_guid)


class folderentry(DynamicAttributes):
    def __init__(self, path, action):
        self.path = path
        self.action = action
        self.delete_folder = False
        self.delete_sub_folders = False
        self.delete_files = False
        self.hidden_folder = False
        self.disabled = False
        self.uid = None
        self.remove_policy = False
        self.bypass_errors = False
        self.apply_once = False
        self.changed = None

    def set_action(self, action):
        self.action = action

    def set_delete_folder(self, del_bool):
        self.delete_folder = del_bool

    def set_delete_sub_folders(self, del_bool):
        self.delete_sub_folders = del_bool

    def set_delete_files(self, del_bool):
        self.delete_files = del_bool

    def set_hidden_folder(self, hid_bool):
        self.hidden_folder = hid_bool

    def set_disabled(self, disabled):
        self.disabled = disabled

    def set_uid(self, uid):
        if uid:
            self.uid = uid
        else:
            self.uid = generate_folder_uid(self)

    def set_remove_policy(self, remove_policy):
        self.remove_policy = remove_policy

    def set_bypass_errors(self, bypass_errors):
        self.bypass_errors = bypass_errors

    def set_apply_once(self, apply_once):
        self.apply_once = apply_once

    def set_changed(self, changed):
        self.changed = utc_to_local(changed)
