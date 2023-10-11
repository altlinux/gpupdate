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

from abc import ABC

import logging
from util.logging import slogm

def check_experimental_enabled(storage):
    experimental_enable_flag = 'Software\\BaseALT\\Policies\\GPUpdate\\GlobalExperimental'
    flag = storage.get_hklm_entry(experimental_enable_flag)

    result = False

    if flag and '1' == str(flag.data):
        result = True

    return result

def check_windows_mapping_enabled(storage):
    windows_mapping_enable_flag = 'Software\\BaseALT\\Policies\\GPUpdate\\WindowsPoliciesMapping'
    flag = storage.get_hklm_entry(windows_mapping_enable_flag)

    result = True

    if flag and '0' == str(flag.data):
        result = False

    return result

def check_module_enabled(storage, module_name):
    gpupdate_module_enable_branch = 'Software\\BaseALT\\Policies\\GPUpdate'
    gpupdate_module_flag = '{}\\{}'.format(gpupdate_module_enable_branch, module_name)
    flag = storage.get_hklm_entry(gpupdate_module_flag)

    result = None

    if flag:
        if '1' == str(flag.data):
            result =  True
        if '0' == str(flag.data):
            result = False

    return result

def check_enabled(storage, module_name, is_experimental):
    module_enabled = check_module_enabled(storage, module_name)
    exp_enabled = check_experimental_enabled(storage)

    result = False

    if None == module_enabled:
        if is_experimental and exp_enabled:
            result = True
        if not is_experimental:
            result = True
    else:
        result = module_enabled

    return result

class applier_frontend(ABC):
    @classmethod
    def __init__(self, regobj):
        pass

    @classmethod
    def apply(self):
        pass

