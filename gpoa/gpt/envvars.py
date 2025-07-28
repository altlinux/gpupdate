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

from util.xml import get_xml_root
from .dynamic_attributes import DynamicAttributes


def read_envvars(envvars_file):
    variables = []

    for var in get_xml_root(envvars_file):
        props = var.find('Properties')
        name = props.get('name')
        value = props.get('value')
        action = props.get('action', default='C')
        var_obj = envvar(name, value, action)

        variables.append(var_obj)

    return variables

def merge_envvars(storage, sid, envvar_objects, policy_name):
    for envv in envvar_objects:
        storage.add_envvar(sid, envv, policy_name)

class envvar(DynamicAttributes):
    def __init__(self, name, value, action):
        self.name = name
        self.value = value
        self.action = action

