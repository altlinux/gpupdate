#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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

# This file is the preferred way to configure Firefox browser in multi-OS
# enterprise environments.
#
# See https://github.com/mozilla/policy-templates/blob/master/README.md
# for more information.
#
# This thing must work with keys and subkeys located at:
# Software\Policies\Mozilla\Firefox

import json
import os

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import log
from util.util import is_machine_name, try_dict_to_literal_eval

class firefox_applier(applier_frontend):
    __module_name = 'FirefoxApplier'
    __module_experimental = False
    __module_enabled = True
    __registry_branch = 'Software/Policies/Mozilla/Firefox'
    __firefox_policies = '/etc/firefox/policies'

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        self._is_machine_name = is_machine_name(self.username)
        self.policies = {}
        self.policies_json = {'policies': self.policies}
        self.firefox_keys = self.storage.filter_hklm_entries(self.__registry_branch)
        self.policies_gen = {}
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )


    def machine_apply(self):
        '''
        Write policies.json to Firefox.
        '''
        excp = ['SOCKSVersion']
        self.policies_json = create_dict(self.firefox_keys, self.__registry_branch, excp)

        destfile = os.path.join(self.__firefox_policies, 'policies.json')
        os.makedirs(self.__firefox_policies, exist_ok=True)
        with open(destfile, 'w') as f:
            json.dump(self.policies_json, f)
            logdata = {'destfile': destfile}
            log('D91', logdata)

    def apply(self):
        if self.__module_enabled:
            log('D93')
            self.machine_apply()
        else:
            log('D94')

def key_dict_is_digit(dictionary:dict) -> bool:
    '''
    Checking if a dictionary key is a digit
    '''
    if not isinstance(dictionary, dict):
        return False
    for dig in dictionary.keys():
        if dig.isdigit():
            return True
    return False


def dict_item_to_list(dictionary:dict) -> dict:
    '''
    Replacing dictionaries with numeric keys with a List
    '''
    if '' in dictionary:
        dictionary = dictionary.pop('')

    for key,val in dictionary.items():
        if type(val) == dict:
            if key_dict_is_digit(val):
                dictionary[key] = [*val.values()]
            else:
                dict_item_to_list(dictionary[key])
    return dictionary

def clean_data_firefox(data):
    return data.replace("'", '\"')



def create_dict(firefox_keys, registry_branch, excp=[]):
    '''
    Collect dictionaries from registry keys into a general dictionary
    '''
    get_boolean = lambda data: data in ['1', 'true', 'True', True, 1] if isinstance(data, (str, int)) else False
    get_parts = lambda hivekey, registry: hivekey.replace(registry, '').split('/')
    counts = {}
    for it_data in firefox_keys:
        branch = counts
        try:
            if type(it_data.data) is bytes:
                it_data.data = it_data.data.decode(encoding='utf-16').replace('\x00','')
            json_data = try_dict_to_literal_eval(it_data.data)
            if json_data:
                it_data.data = json_data
                it_data.type = 7
            else:
                if it_data.type == 1:
                    it_data.data = clean_data_firefox(it_data.data)
            #Cases when it is necessary to create nested dictionaries
            if it_data.valuename != it_data.data:
                parts = get_parts(it_data.hive_key, registry_branch)
                #creating a nested dictionary from elements
                for part in parts[:-1]:
                    branch = branch.setdefault(part, {})
                #dictionary key value initialization
                if it_data.type == 4:
                    if it_data.valuename in excp:
                        branch[parts[-1]] = int(it_data.data)
                    else:
                        branch[parts[-1]] = get_boolean(it_data.data)
                elif it_data.type == 7:
                    branch[parts[-1]] = it_data.data
                else:
                    branch[parts[-1]] = str(it_data.data).replace('\\', '/')
            #Cases when it is necessary to create lists in a dictionary
            else:
                parts = get_parts(it_data.keyname, registry_branch)
                for part in parts[:-1]:
                    branch = branch.setdefault(part, {})
                if branch.get(parts[-1]) is None:
                    branch[parts[-1]] = []
                if it_data.type == 4:
                    branch[parts[-1]].append(get_boolean(it_data.data))
                else:
                    if os.path.isdir(str(it_data.data).replace('\\', '/')):
                        branch[parts[-1]].append(str(it_data.data).replace('\\', '/'))
                    else:
                        branch[parts[-1]].append(str(it_data.data))
        except Exception as exc:
            logdata = {'Exception': exc, 'keyname': it_data.keyname}
            log('W14', logdata)

    return {'policies': dict_item_to_list(counts)}
