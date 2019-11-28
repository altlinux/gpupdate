from .applier_frontend import applier_frontend
from .appliers.systemd import systemd_unit

import logging

from samba.gp_parse.gp_pol import GPPolParser

class systemd_applier(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\SystemdUnits'

    def __init__(self, polfiles):
        self.polparsers = polfiles
        self.systemd_unit_settings = self._get_unit_settings(self.polparsers)
        self.units = []
        for setting in self.systemd_unit_settings:
            try:
                self.units.append(systemd_unit(setting.valuename, setting.data))
            except:
                logging.info('Unable to work with systemd unit: {}'.format(setting.valuename))

    def _get_unit_settings(self, polfiles):
        '''
        Extract control entries from PReg file
        '''
        units = []
        for parser in polfiles:
            for entry in parser.entries:
                if entry.keyname == self.__registry_branch:
                    units.append(entry)
                    logging.info('Found systemd unit setting: {}'.format(entry.valuename))
                else:
                    # Property names are taken from python/samba/gp_parse/gp_pol.py
                    logging.info('Dropped systemd unit setting: {}\\{}'.format(entry.keyname, entry.valuename))
        return units

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for unit in self.units:
            try:
                unit.apply()
            except:
                logging.error('Failed applying unit {}'.format(unit.unit_name))
