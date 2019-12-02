from .applier_frontend import applier_frontend
from .appliers.systemd import systemd_unit

import logging

from samba.gp_parse.gp_pol import GPPolParser

class systemd_applier(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\SystemdUnits'

    def __init__(self, storage):
        self.storage = storage
        self.systemd_unit_settings = self.storage.filter_entries('Software\\BaseALT\\Policies\\SystemdUnits%')
        self.units = []
        for setting in self.systemd_unit_settings:
            valuename = setting.hive_key.rpartition('\\')[2]
            try:
                self.units.append(systemd_unit(valuename, int(setting.data)))
                logging.info('Working with systemd unit {}'.format(valuename))
            except:
                logging.info('Unable to work with systemd unit: {}'.format(valuename))

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for unit in self.units:
            try:
                unit.apply()
            except:
                logging.error('Failed applying unit {}'.format(unit.unit_name))

