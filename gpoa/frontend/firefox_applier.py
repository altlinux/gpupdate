# This file is the preferred way to configure Firefox browser in multi-OS
# enterprise environments.
#
# See https://github.com/mozilla/policy-templates/blob/master/README.md
# for more information.
#
# This thing must work with keys and subkeys located at:
# Software\Policies\Mozilla\Firefox

import logging

from storage import sqlite_registry

import json
import os

class firefox_applier:
    __registry_branch = 'Software\\Policies\\Mozilla\\Firefox'
    __firefox_installdir = '/usr/lib64/firefox/distribution'

    def __init__(self, storage):
        self.storage = storage
        self.policies = dict()
        self.policies_json = dict({ 'policies': self.policies })

    def get_hklm_string_entry(self, hive_subkey):
        '''
        Get HKEY_LOCAL_MACHINE hive subkey of
        'Software\Policies\Mozilla\Firefox'.
        '''
        query_str = '{}\\{}'.format(self.__registry_branch, hive_subkey)
        response = self.storage.get_hklm_entry(query_str)
        return response

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
        self.policies[name] = obj
        logging.info('Firefox policy \'{}\' set to {}'.format(name, obj))

    def get_home_page(self):
        '''
        Query the Homepage property from the storage.
        '''
        homepage = dict({
            'URL': 'about:config',
            'Locked': True,
            'StartPage': 'homepage'
        })
        response = self.get_hklm_string_entry_default('Homepage\\URL', 'about:config')
        homepage['URL'] = response
        return homepage

    def get_block_about_config(self):
        '''
        Query BlockAboutConfig boolean property from the storage.
        '''
        response = self.get_hklm_string_entry_default('BlockAboutConfig', True)
        if response.lower() in ['0', 'false', False]:
            return False
        return True

    def apply(self):
        '''
        Write policies.json to Firefox installdir.
        '''
        self.set_policy('Homepage', self.get_home_page())
        self.set_policy('BlockAboutConfig', self.get_block_about_config())
        destfile = os.path.join(self.__firefox_installdir, 'policies.json')
        with open(destfile, 'w') as f:
            json.dump(self.policies_json, f)

