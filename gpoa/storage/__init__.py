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

from .sqlite_registry import sqlite_registry
from .samba_registry import SambaRegistry
from .sqlite_cache import sqlite_cache

def cache_factory(cache_name):
    return sqlite_cache(cache_name)

def registry_factory(registry_name='registry', registry_dir=None):
    #reg = sqlite_registry(registry_name, registry_dir)
    reg = SambaRegistry()
    return reg
