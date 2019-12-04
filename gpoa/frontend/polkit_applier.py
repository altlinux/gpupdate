from .applier_frontend import applier_frontend
from .appliers.polkit import polkit

import logging
from xml.etree import ElementTree

class polkit_applier(applier_frontend):
    __deny_all = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices\\Deny_All'
    __polkit_map = {
        __deny_all: ['99-gpoa_disk_permissions', { 'Deny_All': 0 }]
    }

    def __init__(self, storage):
        self.storage = storage
        deny_all = storage.filter_hklm_entries(self.__deny_all).first()
        # Deny_All hook: initialize defaults
        template_file = self.__polkit_map[self.__deny_all][0]
        template_vars = self.__polkit_map[self.__deny_all][1]
        if deny_all:
            logging.debug('Deny_All setting found: {}'.format(deny_all.data))
            self.__polkit_map[self.__deny_all][1]['Deny_All'] = deny_all.data
        else:
            logging.debug('Deny_All setting not found')
        self.policies = []
        self.policies.append(polkit(template_file, template_vars))

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for policy in self.policies:
            policy.generate()

