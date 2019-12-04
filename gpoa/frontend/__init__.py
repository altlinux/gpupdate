from storage import sqlite_registry

from .control_applier import control_applier
from .polkit_applier import polkit_applier
from .systemd_applier import systemd_applier
from .firefox_applier import firefox_applier
from .chromium_applier import chromium_applier

import logging

class applier:
    def __init__(self, sid, username):
        self.storage = sqlite_registry('registry')
        self.sid = sid
        self.username = username

        self.appliers = dict({
            'control':  control_applier(self.storage),
            'polkit':   polkit_applier(self.storage),
            'systemd':  systemd_applier(self.storage),
            'firefox':  firefox_applier(self.storage, self.sid, self.username),
            'chromium': chromium_applier(self.storage, self.sid, self.username)
        })

    def apply_parameters(self):
        logging.info('Applying')
        self.appliers['systemd'].apply()
        self.appliers['control'].apply()
        self.appliers['polkit'].apply()
        self.appliers['firefox'].apply()
        self.appliers['chromium'].apply()

