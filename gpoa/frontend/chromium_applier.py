from .applier_frontend import applier_frontend

import logging
import json
import os

class chromium_applier(applier_frontend):
    __registry_branch = 'Software\\Policies\\Chromium'
    __managed_policies_path = '/etc/chromium/policies/managed'
    __recommended_policies_path = '/etc/chromium/policies/recommended'

    def __init__(self, storage):
        self.storage = storage
        self.policies = dict()

    def get_hklm_string_entry(self, hive_subkey):
        query_str = '{}\\{}'.format(self.__registry_branch, hive_subkey)
        return self.storage.get_hklm_entry(query_str)

    def get_hklm_string_entry_default(self, hive_subkey, default):
        defval = str(default)
        response = self.get_hklm_string_entry(hive_subkey)
        if response:
            return response.data
        return defval

    def set_policy(self, name, obj):
        self.policies[name] = obj
        logging.info('Chromium policy \'{}\' set to {}'.format(name, obj))

    def get_home_page(self):
        return self.get_hklm_string_entry_default('HomepageLocation', 'about:blank')

    def apply(self):
        self.set_policy('HomepageLocation', self.get_home_page())

        destfile = os.path.join(self.__managed_policies_path, 'policies.json')

        os.makedirs(self.__managed_policies_path, exist_ok=True)
        with open(destfile, 'w') as f:
            json.dump(self.policies, f)
            logging.info('Wrote Chromium preferences to {}'.format(destfile))

