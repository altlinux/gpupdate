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
        for key, value in kwargs.items():
            self.__setattr__(key, value)

    def __setattr__(self, key, value):
        if isinstance(value, Enum):
            value = str(value)
        if isinstance(value, str):
            for q in ["'", "\""]:
                if any(q in ch for ch in value):
                    value = value.replace(q, "″")
        self.__dict__[key] = value

    def items(self):
        return self.__dict__.items()

    def __iter__(self):
        return iter(self.__dict__.items())

class RegistryKeyMetadata(DynamicAttributes):
    def __init__(self, policy_name, type, is_list=None, mod_previous_value=None):
        self.policy_name = policy_name
        self.type = type
        self.reloaded_with_policy_key = None
        self.is_list = is_list
        self.mod_previous_value = mod_previous_value

    def __repr__(self):
        return str(dict(self))