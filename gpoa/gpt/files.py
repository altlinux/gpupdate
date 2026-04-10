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

from util.xml import get_xml_root
from util.gpp_lifecycle import generate_file_uid

from .dynamic_attributes import DynamicAttributes
from .filter import parse_filters


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
        fil_obj.set_disabled(fil.get('disabled') == '1')

        # Lifecycle attributes
        fil_obj.set_uid(fil.get('uid'))
        fil_obj.set_remove_policy(fil.get('removePolicy') == '1')
        fil_obj.set_bypass_errors(fil.get('bypassErrors') == '1')
        fil_obj.set_changed(fil.get('changed'))

        # Check for FilterRunOnce
        filters = fil.find('Filters')
        if filters is not None:
            run_once = filters.find('FilterRunOnce')
            fil_obj.set_apply_once(run_once is not None)
        else:
            fil_obj.set_apply_once(False)

        # Parse and add filters
        parsed_filters = parse_filters(fil)
        if parsed_filters:
            fil_obj.filters = parsed_filters

        files.append(fil_obj)

    return files

def merge_files(storage, file_objects, policy_name, policy_guid=None):
    for fileobj in file_objects:
        storage.add_file(fileobj, policy_name, policy_guid)

class fileentry(DynamicAttributes):
    def __init__(self, fromPath):
        self.fromPath = fromPath
        self.action = None
        self.targetPath = None
        self.readOnly = None
        self.archive = None
        self.hidden = None
        self.suppress = None
        self.executable = None
        self.disabled = False
        self.uid = None
        self.remove_policy = False
        self.bypass_errors = False
        self.apply_once = False
        self.changed = None

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
    def set_disabled(self, disabled):
        self.disabled = disabled
    def set_uid(self, uid):
        if uid:
            self.uid = uid
        else:
            self.uid = generate_file_uid(self)
    def set_remove_policy(self, remove_policy):
        self.remove_policy = remove_policy
    def set_bypass_errors(self, bypass_errors):
        self.bypass_errors = bypass_errors
    def set_apply_once(self, apply_once):
        self.apply_once = apply_once
    def set_changed(self, changed):
        self.changed = changed
