from .applier_frontend import applier_frontend
from .appliers.polkit import polkit

import logging
from xml.etree import ElementTree

from samba.gp_parse.gp_pol import GPPolParser

class polkit_applier(applier_frontend):
    __registry_branch = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices'
    __policy_map = {
            'Deny_All': ['99-gpoa_disk_permissions', { 'Deny_All': 0 }]
    }

    def __init__(self, entries):
        self.entries = entries
        self.polkit_settings = self._filter_entries()
        self.policies = []
        for setting in self.polkit_settings:
            if setting.valuename in self.__policy_map.keys() and setting.keyname == self.__registry_branch:
                logging.info('Found key: {}, file: {} and value: {}'.format(setting.keyname, self.__policy_map[setting.valuename][0], self.__policy_map[setting.valuename][1]))
                try:
                   self.__policy_map[setting.valuename][1][setting.valuename] = setting.data
                   self.policies.append(polkit(self.__policy_map[setting.valuename][0], self.__policy_map[setting.valuename][1]))
                except Exception as exc:
                    print(exc)
                    logging.info('Unable to work with PolicyKit setting: {}'.format(setting.valuename))
        #for e in polfile.pol_file.entries:
        #    print('{}:{}:{}:{}:{}'.format(e.type, e.data, e.valuename, e.keyname))

    def _filter_entries(self):
        '''
        Extract control entries from PReg file
        '''
        policies = []
        for entry in self.entries:
            if entry.keyname == self.__registry_branch:
                policies.append(entry)
                logging.info('Found PolicyKit setting: {}\\{}'.format(entry.keyname, entry.valuename))
            else:
                # Property names are taken from python/samba/gp_parse/gp_pol.py
                logging.info('Dropped PolicyKit setting: {}\\{}'.format(entry.keyname, entry.valuename))

        return policies

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for policy in self.policies:
            policy.generate()

