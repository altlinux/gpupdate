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

from util.preg import (
      load_preg
)

def read_polfile(filename):
    return load_preg(filename).entries

def merge_polfile(storage, sid, policy_objects, policy_name):
    pass
    # for entry in policy_objects:
    #     if not sid:
    #         storage.add_hklm_entry(entry, policy_name)
    #     else:
    #         storage.add_hkcu_entry(entry, sid, policy_name)

