from storage import registry_factory

from .control_applier import control_applier
from .polkit_applier import polkit_applier
from .systemd_applier import systemd_applier
from .firefox_applier import firefox_applier
from .chromium_applier import chromium_applier
import util

import logging

class applier:
    def __init__(self, username):
        self.storage = registry_factory('registry')
        self.username = username
        self.sid = util.get_sid(self.storage.get_info('domain'), self.username)

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

