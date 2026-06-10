#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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


class DynamicAttributes:
    def __init__(self, **kwargs):
        self.policy_name = None
        self.filters = []
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    def __setattr__(self, key, value):
        if isinstance(value, Enum):
            value = str(value)
        if isinstance(value, str):
            value = value.replace("'", "′")
            value = value.replace('"', "″")
        self.__dict__[key] = value

    def items(self):
        # Return items with filters last
        filters_val = None
        for k, v in self.__dict__.items():
            if k == 'filters':
                filters_val = v
                continue
            yield (k, v)
        if filters_val is not None:
            if isinstance(filters_val, list):
                filters_val = [dict(f) for f in filters_val]
            yield ('filters', filters_val)

    def __iter__(self):
        return iter(self.items())

    def get_original_value(self, key):
        value = self.__dict__.get(key)
        if isinstance(value, str):
            value = value.replace("′", "'")
            value = value.replace("″", '"')
        return value

class RegistryKeyMetadata(DynamicAttributes):
    def __init__(self, policy_name, type, is_list=None, mod_previous_value=None):
        self.policy_name = policy_name
        self.type = type
        self.reloaded_with_policy_key = None
        self.is_list = is_list
        self.mod_previous_value = mod_previous_value

    def __repr__(self):
        return str(dict(self))