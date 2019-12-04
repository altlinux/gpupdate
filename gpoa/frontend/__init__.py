from storage import sqlite_registry

from .control_applier import control_applier
from .polkit_applier import polkit_applier
from .systemd_applier import systemd_applier
from .firefox_applier import firefox_applier
from .chromium_applier import chromium_applier

import logging

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

        self.appliers = dict({
            'control':  control_applier(self.storage),
            'polkit':   polkit_applier(self.storage),
            'systemd':  systemd_applier(self.storage),
            'firefox':  firefox_applier(self.storage),
            'chromium': chromium_applier(self.storage)
        })

    def apply_parameters(self):
        logging.info('Applying')
        self.appliers['systemd'].apply()
        self.appliers['control'].apply()
        self.appliers['polkit'].apply()
        self.appliers['firefox'].apply()
        self.appliers['chromium'].apply()

