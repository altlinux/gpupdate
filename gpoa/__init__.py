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

import importlib
import os
import sys

_gpoa_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_gpoa_dir)
_gpoa_lib_path = os.path.join(_parent_dir, 'gpoa_lib')

if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

if _gpoa_dir not in sys.path:
    sys.path.insert(0, _gpoa_dir)


def _reexport_module(aliases):
    for alias, target in aliases.items():
        parts = target.rsplit('.', 1)
        if len(parts) == 2:
            mod_path, attr_name = parts
            mod = importlib.import_module(mod_path)
            globals()[alias] = getattr(mod, attr_name)
        else:
            globals()[alias] = importlib.import_module(target)
