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
from util.util import utc_to_local
from util.gpp_lifecycle import generate_envvar_uid

from .dynamic_attributes import DynamicAttributes
from .filter import parse_filters


def read_envvars(envvars_file):
    variables = []

    for var in get_xml_root(envvars_file):
        props = var.find('Properties')
        name = props.get('name')
        value = props.get('value')
        action = props.get('action', default='C')
        var_obj = envvar(name, value, action)
        var_obj.set_disabled(var.get('disabled') == '1')

        # Lifecycle attributes
        var_obj.set_uid(var.get('uid'))
        var_obj.set_remove_policy(var.get('removePolicy') == '1')
        var_obj.set_bypass_errors(var.get('bypassErrors') == '1')
        var_obj.set_changed(var.get('changed'))

        # Check for FilterRunOnce
        filters = var.find('Filters')
        if filters is not None:
            run_once = filters.find('FilterRunOnce')
            var_obj.set_apply_once(run_once is not None)
        else:
            var_obj.set_apply_once(False)

        # Parse and add filters
        filters = parse_filters(var)
        if filters:
            var_obj.filters = filters

        variables.append(var_obj)

    return variables

def merge_envvars(storage, envvar_objects, policy_name, policy_guid=None):
    for envv in envvar_objects:
        storage.add_envvar(envv, policy_name, policy_guid)

class envvar(DynamicAttributes):
    def __init__(self, name, value, action):
        self.name = name
        self.value = value
        self.action = action
        self.disabled = False
        self.uid = None
        self.remove_policy = False
        self.bypass_errors = False
        self.apply_once = False
        self.changed = None

    def set_disabled(self, disabled):
        self.disabled = disabled

    def set_uid(self, uid):
        if uid:
            self.uid = uid
        else:
            self.uid = generate_envvar_uid(self)

    def set_remove_policy(self, remove_policy):
        self.remove_policy = remove_policy

    def set_bypass_errors(self, bypass_errors):
        self.bypass_errors = bypass_errors

    def set_apply_once(self, apply_once):
        self.apply_once = apply_once

    def set_changed(self, changed):
        self.changed = utc_to_local(changed)

