#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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

from util.xml import get_xml_root
from .dynamic_attributes import DynamicAttributes

def read_files(filesxml):
    files = []

    for fil in get_xml_root(filesxml):
        props = fil.find('Properties')
        fil_obj = fileentry(props.get('fromPath'))
        fil_obj.set_action(props.get('action', default='C'))
        fil_obj.set_target_path(props.get('targetPath', default=None))
        fil_obj.set_read_only(props.get('readOnly', default=None))
        fil_obj.set_archive(props.get('archive', default=None))
        fil_obj.set_hidden(props.get('hidden', default=None))
        fil_obj.set_suppress(props.get('suppress', default=None))
        fil_obj.set_executable(props.get('executable', default=None))
        files.append(fil_obj)

    return files

def merge_files(storage, file_objects, policy_name):
    for fileobj in file_objects:
        storage.add_file(fileobj, policy_name)

class fileentry(DynamicAttributes):
    def __init__(self, fromPath):
        self.fromPath = fromPath

    def set_action(self, action):
        self.action = action
    def set_target_path(self, targetPath):
        self.targetPath = targetPath
    def set_read_only(self, readOnly):
        self.readOnly = readOnly
    def set_archive(self, archive):
        self.archive = archive
    def set_hidden(self, hidden):
        self.hidden = hidden
    def set_suppress(self, suppress):
        self.suppress = suppress
    def set_executable(self, executable):
        self.executable = executable
