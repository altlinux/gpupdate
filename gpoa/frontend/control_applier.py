from .applier_frontend import applier_frontend
from .appliers.control import control

import logging

from samba.gp_parse.gp_pol import GPPolParser

class control_applier(applier_frontend):
    _registry_branch = 'Software\\BaseALT\\Policies\\Control'

    def __init__(self, storage):
        self.storage = storage
        self.control_settings = self.storage.filter_entries('Software\\BaseALT\\Policies\\Control%')
        self.controls = list()
        for setting in self.control_settings:
            valuename = setting.hive_key.rpartition('\\')[2]
            try:
                self.controls.append(control(valuename, int(setting.data)))
                logging.info('Working with control {}'.format(valuename))
            except:
                logging.info('Unable to work with control: {}'.format(valuename))
        #for e in polfile.pol_file.entries:
        #    print('{}:{}:{}:{}:{}'.format(e.type, e.data, e.valuename, e.keyname))

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for cont in self.controls:
            cont.set_control_status()

