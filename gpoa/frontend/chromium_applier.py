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

from .applier_frontend import applier_frontend

import logging
import json
import os

from util.logging import slogm
from util.util import is_machine_name

class chromium_applier(applier_frontend):
    __registry_branch = 'Software\\Policies\\Google\\Chrome'
    __managed_policies_path = '/etc/chromium/policies/managed'
    __recommended_policies_path = '/etc/chromium/policies/recommended'
    # JSON file where Chromium stores its settings (and which is
    # overwritten every exit.
    __user_settings = '.config/chromium/Default'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self._is_machine_name = is_machine_name(self.username)
        self.policies = dict()

    def get_hklm_string_entry(self, hive_subkey):
        query_str = '{}\\{}'.format(self.__registry_branch, hive_subkey)
        return self.storage.get_hklm_entry(query_str)

    def get_hkcu_string_entry(self, hive_subkey):
        query_str = '{}\\{}'.format(self.__registry_branch, hive_subkey)
        return self.storage.get_hkcu_entry(sid, query_str)

    def get_hklm_string_entry_default(self, hive_subkey, default):
        '''
        Return row from HKLM table identified by hive_subkey as string
        or return supplied default value if such hive_subkey is missing.
        '''

        defval = str(default)
        response = self.get_hklm_string_entry(hive_subkey)

        if response:
            return response.data

        return defval

    def get_hkcu_string_entry_default(self, hive_subkey, default):
        defval = str(default)
        response = self.get_hkcu_string_entry(hive_subkey)
        if response:
            return response.data
        return defval

    def set_policy(self, name, obj):
        if obj:
            self.policies[name] = obj
            logging.info(slogm('Chromium policy \'{}\' set to {}'.format(name, obj)))

    def set_user_policy(self, name, obj):
        '''
        Please not that writing user preferences file is not considered
        a good practice and used mostly by various malware.
        '''
        if not self._is_machine_name:
            prefdir = os.path.join(util.get_homedir(self.username), self.__user_settings)
            os.makedirs(prefdir, exist_ok=True)

            prefpath = os.path.join(prefdir, 'Preferences')
            util.mk_homedir_path(self.username, self.__user_settings)
            settings = dict()
            try:
                with open(prefpath, 'r') as f:
                    settings = json.load(f)
            except FileNotFoundError as exc:
                logging.error(slogm('Chromium preferences file {} does not exist at the moment'.format(prefpath)))
            except:
                logging.error(slogm('Error during attempt to read Chromium preferences for user {}'.format(self.username)))

            if obj:
                settings[name] = obj

                with open(prefpath, 'w') as f:
                    json.dump(settings, f)
                logging.info(slogm('Set user ({}) property \'{}\' to {}'.format(self.username, name, obj)))

    def get_home_page(self, hkcu=False):
        response = self.get_hklm_string_entry('HomepageLocation')
        result = 'about:blank'
        if response:
            result = response.data
        return result

    def machine_apply(self):
        '''
        Apply machine settings.
        '''
        self.set_policy('HomepageLocation', self.get_home_page())

        destfile = os.path.join(self.__managed_policies_path, 'policies.json')

        os.makedirs(self.__managed_policies_path, exist_ok=True)
        with open(destfile, 'w') as f:
            json.dump(self.policies, f)
            logging.debug(slogm('Wrote Chromium preferences to {}'.format(destfile)))

    def user_apply(self):
        '''
        Apply settings for the specified username.
        '''
        self.set_user_policy('homepage', self.get_home_page(hkcu=True))

    def apply(self):
        '''
        All actual job done here.
        '''
        self.machine_apply()
        #if not self._is_machine_name:
        #    logging.debug('Running user applier for Chromium')
        #    self.user_apply()
