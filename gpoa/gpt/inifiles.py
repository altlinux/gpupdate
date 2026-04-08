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
from util.gpp_lifecycle import get_or_generate_uid, generate_ini_uid

from .dynamic_attributes import DynamicAttributes


def read_inifiles(inifiles_file):
    inifiles = []

    for ini in get_xml_root(inifiles_file):
        props = ini.find('Properties')
        ini_obj = inifile(props.get('path'))
        ini_obj.set_section(props.get('section', default=None))
        ini_obj.set_property(props.get('property', default=None))
        ini_obj.set_value(props.get('value', default=None))
        ini_obj.set_action(props.get('action', default='C'))

        # Lifecycle attributes from element
        ini_obj.set_uid(ini.get('uid'))
        ini_obj.set_disabled(ini.get('disabled') == '1')
        ini_obj.set_remove_policy(ini.get('removePolicy') == '1')
        ini_obj.set_bypass_errors(ini.get('bypassErrors') == '1')
        ini_obj.set_changed(ini.get('changed'))

        # Check for FilterRunOnce
        filters = ini.find('Filters')
        if filters is not None:
            run_once = filters.find('FilterRunOnce')
            ini_obj.set_apply_once(run_once is not None)
        else:
            ini_obj.set_apply_once(False)

        inifiles.append(ini_obj)

    return inifiles

def merge_inifiles(storage, inifile_objects, policy_name):
    for iniobj in inifile_objects:
        storage.add_ini(iniobj, policy_name)

class inifile(DynamicAttributes):
    def __init__(self, path):
        self.path = path
        self.section = None
        self.property = None
        self.value = None
        self.action = None
        self.uid = None
        self.disabled = False
        self.remove_policy = False
        self.bypass_errors = False
        self.apply_once = False
        self.changed = None

    def set_section(self, section):
        self.section = section
    def set_property(self, property):
        self.property = property
    def set_value(self, value):
        self.value = value
    def set_action(self, action):
        self.action = action
    def set_uid(self, uid):
        if uid:
            self.uid = uid
        else:
            self.uid = generate_ini_uid(self)
    def set_disabled(self, disabled):
        self.disabled = disabled
    def set_remove_policy(self, remove_policy):
        self.remove_policy = remove_policy
    def set_bypass_errors(self, bypass_errors):
        self.bypass_errors = bypass_errors
    def set_apply_once(self, apply_once):
        self.apply_once = apply_once
    def set_changed(self, changed):
        self.changed = changed

