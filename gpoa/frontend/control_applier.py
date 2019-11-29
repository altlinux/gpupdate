from .applier_frontend import applier_frontend
from .appliers.control import control

import logging

from samba.gp_parse.gp_pol import GPPolParser

class control_applier(applier_frontend):
    _registry_branch = 'Software\\BaseALT\\Policies\\Control'

    def __init__(self, entries):
        self.entries = entries
        self.control_settings = self._filter_entries()
        self.controls = []
        for setting in self.control_settings:
            try:
                self.controls.append(control(setting.valuename, setting.data))
            except:
                logging.info('Unable to work with control: {}'.format(setting.valuename))
        #for e in polfile.pol_file.entries:
        #    print('{}:{}:{}:{}:{}'.format(e.type, e.data, e.valuename, e.keyname))

    def _filter_entries(self):
        '''
        Extract control entries from PReg file
        '''
        controls = []
        for entry in self.entries:
            if entry.keyname == self._registry_branch:
                controls.append(entry)
                logging.info('Found control setting: {}'.format(entry.valuename))
            else:
                # Property names are taken from python/samba/gp_parse/gp_pol.py
                logging.info('Dropped control setting: {}\\{}'.format(entry.keyname, entry.valuename))
        return controls

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for cont in self.controls:
            cont.set_control_status()

