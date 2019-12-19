from storage import registry_factory

from .control_applier import control_applier
from .polkit_applier import polkit_applier
from .systemd_applier import systemd_applier
from .firefox_applier import firefox_applier
from .chromium_applier import chromium_applier
from .shortcut_applier import shortcut_applier
import util

import logging

import pwd
import os

class applier:
    def __init__(self, username, target):
        self.storage = registry_factory('registry')
        self.username = username
        self.target = target
        self.sid = util.get_sid(self.storage.get_info('domain'), self.username)

        self.process_uid = os.getuid()
        self.process_uname = pwd.getpwuid(self.process_uid).pw_name

        self.appliers = dict({
            'control':  control_applier(self.storage),
            'polkit':   polkit_applier(self.storage),
            'systemd':  systemd_applier(self.storage),
            'firefox':  firefox_applier(self.storage, self.sid, self.username),
            'chromium': chromium_applier(self.storage, self.sid, self.username),
            'shortcuts': shortcut_applier(self.storage, self.sid, self.username)
        })

    def apply_parameters(self):
        if 'All' == self.target or 'Computer' == self.target:
            logging.debug('Applying computer part of settings')
            if 0 != self.process_uid:
                logging.error('Not sufficient privileges to run machine appliers')
                return
            self.appliers['systemd'].apply()
            self.appliers['control'].apply()
            self.appliers['polkit'].apply()
            self.appliers['firefox'].apply()
            self.appliers['chromium'].apply()
            self.appliers['shortcuts'].apply()
        if self.storage.get_info('machine_sid') != self.sid:
            if 'All' == self.target or 'User' == self.target:
                if 0 == self.process_uid:
                    logging.error('Userspace applier must not be run by root')
                logging.debug('There are no user settings appliers at the moment')

