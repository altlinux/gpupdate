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
import util
import configparser

from .applier_frontend import applier_frontend

class firefox_applier(applier_frontend):
    __registry_branch = 'Software\\Policies\\Mozilla\\Firefox'
    __firefox_installdir = '/usr/lib64/firefox/distribution'
    __user_settings_dir = '.mozilla/firefox'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self._is_machine_name = util.is_machine_name(self.username)
        self.policies = dict()
        self.policies_json = dict({ 'policies': self.policies })

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
            logging.info('Firefox policy \'{}\' set to {}'.format(name, obj))

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
            homepage['URL'] = response
            return homepage
        return None

    def get_block_about_config(self):
        '''
        Query BlockAboutConfig boolean property from the storage.
        '''
        response = self.get_hklm_string_entry('BlockAboutConfig')
        if response:
            if response.lower() in ['0', 'false', False, None, 'None']:
                return False
            return True

        return None

    def machine_apply(self):
        '''
        Write policies.json to Firefox installdir.
        '''
        self.set_policy('Homepage', self.get_home_page())
        self.set_policy('BlockAboutConfig', self.get_block_about_config())

        destfile = os.path.join(self.__firefox_installdir, 'policies.json')

        os.makedirs(self.__firefox_installdir, exist_ok=True)
        with open(destfile, 'w') as f:
            json.dump(self.policies_json, f)
            logging.debug('Wrote Firefox preferences to {}'.format(destfile))

    def user_apply(self):
        profiles = self.get_profiles()

        profiledir = os.path.join(util.get_homedir(self.username), self.__user_settings_dir)
        for profile in profiles:
            logging.debug('Found Firefox profile in {}/{}'.format(profiledir, profile))

    def apply(self):
        self.machine_apply()
        #if not self._is_machine_name:
        #    logging.debug('Running user applier for Firefox')
        #    self.user_apply()

