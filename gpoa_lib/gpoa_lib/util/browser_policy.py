#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

import json

from .util import string_to_literal_eval


def is_json_object(value):
    """Distinguish object-valued REG_SZ from numbered registry subkeys."""
    if not isinstance(value, str) or not value.lstrip().startswith('{'):
        return False
    try:
        return isinstance(json.loads(value), dict)
    except ValueError:
        return False


def browser_policy_values(settings):
    result = {}
    for key, value in settings.items():
        if type(value) is dict:
            # Registry subkeys represent the existing list-policy format.
            result[key] = list(value.values())
        elif is_json_object(value):
            # Decode only at output: otherwise this object would become a list.
            result[key] = json.loads(value)
        else:
            result[key] = string_to_literal_eval(value)
    return result
