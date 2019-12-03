from storage import sqlite_registry

from .appliers.control import control
from .appliers.polkit import polkit
from .appliers.systemd import systemd_unit

from .control_applier import control_applier
from .polkit_applier import polkit_applier
from .systemd_applier import systemd_applier

import logging
#from xml.etree import ElementTree

class entry:
    def __init__(self, e_keyname, e_valuename, e_type, e_data):
        self.keyname = e_keyname
        self.valuename = e_valuename
        self.type = e_type
        self.data = e_data

def preg2entries(preg_obj):
    entries = []
    for elem in prej_obj.entries:
        entry_obj = entry(elem.keyname, elem.valuename, elem.type, elem.data)
        entries.append(entry_obj)
    return entries

class applier:
    def __init__(self, sid):
        self.storage = sqlite_registry('registry')
        capplier = control_applier(self.storage)
        pkapplier = polkit_applier(self.storage)
        sdapplier = systemd_applier(self.storage)
        self.appliers = dict({ 'control': capplier, 'polkit': pkapplier, 'systemd': sdapplier })

    def apply_parameters(self):
        logging.info('Applying')
        self.appliers['control'].apply()
        self.appliers['polkit'].apply()
        self.appliers['systemd'].apply()

