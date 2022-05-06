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

import logging
import json
import os
import configparser

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import slogm, log
from util.util import is_machine_name, get_homedir

class firefox_applier(applier_frontend):
    __module_name = 'FirefoxApplier'
    __module_experimental = False
    __module_enabled = True
    __registry_branch = 'Software\\Policies\\Mozilla\\Firefox'
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
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def get_profiles(self):
        '''
        Get directory names of Firefox profiles for specified username.
        '''
        profiles_ini = os.path.join(get_homedir(self.username), self.__user_settings_dir, 'profiles.ini')
        config = configparser.ConfigParser()
        config.read(profiles_ini)

        profile_paths = list()
        for section in config.keys():
            if section.startswith('Profile'):
                profile_paths.append(config[section]['Path'])

        return profile_paths

    def get_hklm_string_entry(self, hive_subkey):
        '''
        Get HKEY_LOCAL_MACHINE hive subkey of
        'Software\Policies\Mozilla\Firefox'.
        '''
        query_str = '{}\\{}'.format(self.__registry_branch, hive_subkey)
        return self.storage.get_hklm_entry(query_str)

    def get_hklm_string_entry_default(self, hive_subkey, default):
        '''
        Get Firefox's subkey or return the default value.
        '''
        defval = str(default)
        response = self.get_hklm_string_entry(hive_subkey)
        if response:
            return response.data
        return defval

    def set_policy(self, name, obj):
        '''
        Add entry to policy set.
        '''
        if obj:
            self.policies[name] = obj
            logdata = dict()
            logdata['name'] = name
            logdata['set to'] = obj
            log('I7', logdata)

    def get_home_page(self):
        '''
        Query the Homepage property from the storage.
        '''
        homepage = dict({
            'URL': 'about:blank',
            'Locked': False,
            'StartPage': 'homepage'
        })
        response = self.get_hklm_string_entry('Homepage\\URL')
        if response:
            homepage['URL'] = response.data
            return homepage
        return None

    def get_boolean_config(self, name):
        '''
        Query boolean property from the storage.
        '''
        response = self.get_hklm_string_entry(name)
        if response:
            data = response.data if isinstance(response.data, int) else str(response.data).lower()
            if data in ['0', 'false', None, 'none', 0]:
                return False
            if data in ['1', 'true', 1]:
                return True

        return None

    def set_boolean_policy(self, name):
        '''
        Add boolean entry to policy set.
        '''
        obj = self.get_boolean_config(name)
        if obj is not None:
            self.policies[name] = obj
            logdata = dict()
            logdata['name'] = name
            logdata['set to'] = obj
            log('I7', logdata)

    def machine_apply(self):
        '''
        Write policies.json to Firefox installdir.
        '''
        self.set_policy('Homepage', self.get_home_page())
        self.set_boolean_policy('BlockAboutConfig')
        self.set_boolean_policy('BlockAboutProfiles')
        self.set_boolean_policy('BlockAboutSupport')
        self.set_boolean_policy('CaptivePortal')
        self.set_boolean_policy('DisableSetDesktopBackground')
        self.set_boolean_policy('DisableMasterPasswordCreation')
        self.set_boolean_policy('DisableBuiltinPDFViewer')
        self.set_boolean_policy('DisableDeveloperTools')
        self.set_boolean_policy('DisableFeedbackCommands')
        self.set_boolean_policy('DisableFirefoxScreenshots')
        self.set_boolean_policy('DisableFirefoxAccounts')
        self.set_boolean_policy('DisableFirefoxStudies')
        self.set_boolean_policy('DisableForgetButton')
        self.set_boolean_policy('DisableFormHistory')
        self.set_boolean_policy('DisablePasswordReveal')
        self.set_boolean_policy('DisablePocket')
        self.set_boolean_policy('DisablePrivateBrowsing')
        self.set_boolean_policy('DisableProfileImport')
        self.set_boolean_policy('DisableProfileRefresh')
        self.set_boolean_policy('DisableSafeMode')
        self.set_boolean_policy('DisableSystemAddonUpdate')
        self.set_boolean_policy('DisableTelemetry')
        self.set_boolean_policy('DontCheckDefaultBrowser')
        self.set_boolean_policy('ExtensionUpdate')
        self.set_boolean_policy('HardwareAcceleration')
        self.set_boolean_policy('PrimaryPassword')
        self.set_boolean_policy('NetworkPrediction')
        self.set_boolean_policy('NewTabPage')
        self.set_boolean_policy('NoDefaultBookmarks')
        self.set_boolean_policy('OfferToSaveLogins')
        self.set_boolean_policy('PasswordManagerEnabled')
        self.set_boolean_policy('PromptForDownloadLocation')
        self.set_boolean_policy('SanitizeOnShutdown')
        self.set_boolean_policy('SearchSuggestEnabled')

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

        profiledir = os.path.join(get_homedir(self.username), self.__user_settings_dir)
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
        #if not self._is_machine_name:
        #    logging.debug('Running user applier for Firefox')
        #    self.user_apply()

