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
from storage.dconf_registry import Dconf_registry

from enum import Enum

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

def read_envvars(envvars_file):
    variables = list()

    for var in get_xml_root(envvars_file):
        props = var.find('Properties')
        name = props.get('name')
        value = props.get('value')
        var_obj = envvar(name, value)
        var_obj.set_action(action_letter2enum(props.get('action', default='C')))

        variables.append(var_obj)

    Dconf_registry.environmentvariables.append(variables)
    return variables

def merge_envvars(storage, sid, envvar_objects, policy_name):
    for envv in envvar_objects:
        storage.add_envvar(sid, envv, policy_name)

class envvar:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.action = FileAction.CREATE

    def set_action(self, action):
        self.action = action

