from .applier_frontend import applier_frontend
from .appliers.systemd import systemd_unit
from util.logging import slogm

import logging

class systemd_applier(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\SystemdUnits'

    def __init__(self, storage):
        self.storage = storage
        self.systemd_unit_settings = self.storage.filter_hklm_entries('Software\\BaseALT\\Policies\\SystemdUnits%')
        self.units = []

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for setting in self.systemd_unit_settings:
            valuename = setting.hive_key.rpartition('\\')[2]
            try:
                self.units.append(systemd_unit(valuename, int(setting.data)))
                logging.info(slogm('Working with systemd unit {}'.format(valuename)))
            except Exception as exc:
                logging.info(slogm('Unable to work with systemd unit {}: {}'.format(valuename, exc)))
        for unit in self.units:
            try:
                unit.apply()
            except:
                logging.error(slogm('Failed applying unit {}'.format(unit.unit_name)))

