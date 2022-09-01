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
import configparser

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import log
from util.util import is_machine_name
import util.util as util

class firefox_applier(applier_frontend):
    __module_name = 'FirefoxApplier'
    __module_experimental = False
    __module_enabled = True
    __registry_branch = 'Software\\Policies\\Mozilla\\Firefox\\'
    __firefox_installdir1 = '/usr/lib64/firefox/distribution'
    __firefox_installdir2 = '/etc/firefox/policies'
    __user_settings_dir = '.mozilla/firefox'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self._is_machine_name = is_machine_name(self.username)
        self.policies = dict()
        self.policies_json = dict({ 'policies': self.policies })
        firefox_filter = '{}%'.format(self.__registry_branch)
        self.firefox_keys = self.storage.filter_hklm_entries(firefox_filter)
        self.policies_gen = dict()
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def get_profiles(self):
        '''
        Get directory names of Firefox profiles for specified username.
        '''
        profiles_ini = os.path.join(util.get_homedir(self.username), self.__user_settings_dir, 'profiles.ini')
        config = configparser.ConfigParser()
        config.read(profiles_ini)

        profile_paths = list()
        for section in config.keys():
            if section.startswith('Profile'):
                profile_paths.append(config[section]['Path'])
        return profile_paths

    def get_boolean(self,data):
        if data in ['0', 'false', None, 'none', 0]:
            return False
        if data in ['1', 'true', 1]:
            return True

    def get_parts(self, hivekeyname):
        '''
        Parse registry path string and leave key parameters
        '''
        parts = hivekeyname.replace(self.__registry_branch, '').split('\\')
        return parts

    def create_dict(self, firefox_keys):
        '''
        Collect dictionaries from registry keys into a general dictionary
        '''
        counts = dict()
        for it_data in firefox_keys:
            branch = counts
            try:
                if type(it_data.data) is bytes:
                    it_data.data = it_data.data.decode(encoding='utf-16').replace('\x00','')
                #Cases when it is necessary to create nested dictionaries
                if it_data.valuename != it_data.data:
                    parts = self.get_parts(it_data.hive_key)
                    #creating a nested dictionary from elements
                    for part in parts[:-1]:
                        branch = branch.setdefault(part, {})
                    #dictionary key value initialization
                    if it_data.type == 4:
                        branch[parts[-1]] = self.get_boolean(it_data.data)
                    else:
                        branch[parts[-1]] = str(it_data.data).replace('\\', '/')
                #Cases when it is necessary to create lists in a dictionary
                else:
                    parts = self.get_parts(it_data.keyname)
                    for part in parts[:-1]:
                        branch = branch.setdefault(part, {})
                    if branch.get(parts[-1]) is None:
                        branch[parts[-1]] = list()
                    if it_data.type == 4:
                        branch[parts[-1]].append(self.get_boolean(it_data.data))
                    else:
                        if os.path.isdir(str(it_data.data).replace('\\', '/')):
                            branch[parts[-1]].append(str(it_data.data).replace('\\', '/'))
                        else:
                            branch[parts[-1]].append(str(it_data.data))
            except Exception as exc:
                logdata = dict()
                logdata['Exception'] = exc
                logdata['keyname'] = it_data.keyname
                log('W14', logdata)

        self.policies_json = {'policies': dict_item_to_list(counts)}

    def machine_apply(self):
        '''
        Write policies.json to Firefox installdir.
        '''
        self.create_dict(self.firefox_keys)
        destfile = os.path.join(self.__firefox_installdir1, 'policies.json')

        os.makedirs(self.__firefox_installdir1, exist_ok=True)
        with open(destfile, 'w') as f:
            json.dump(self.policies_json, f)
            logdata = dict()
            logdata['destfile'] = destfile
            log('D91', logdata)

        destfile = os.path.join(self.__firefox_installdir2, 'policies.json')
        os.makedirs(self.__firefox_installdir2, exist_ok=True)
        with open(destfile, 'w') as f:
            json.dump(self.policies_json, f)
            logdata = dict()
            logdata['destfile'] = destfile
            log('D91', logdata)

    def user_apply(self):
        profiles = self.get_profiles()

        profiledir = os.path.join(util.get_homedir(self.username), self.__user_settings_dir)
        for profile in profiles:
            logdata = dict()
            logdata['profiledir'] = profiledir
            logdata['profile'] = profile
            log('D92', logdata)

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
    for key,val in dictionary.items():
        if type(val) == dict:
            if key_dict_is_digit(val):
                dictionary[key] = [*val.values()]
            else:
                dict_item_to_list(dictionary[key])
    return dictionary
