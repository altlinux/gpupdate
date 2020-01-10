#
# Copyright (C) 2019-2020 Igor Chudov
# Copyright (C) 2019-2020 Evgeny Sinelnikov
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from storage import registry_factory

from .control_applier import control_applier
from .polkit_applier import polkit_applier
from .systemd_applier import systemd_applier
from .firefox_applier import firefox_applier
from .chromium_applier import chromium_applier
from .cups_applier import cups_applier
from .package_applier import package_applier
from .shortcut_applier import (
    shortcut_applier,
    shortcut_applier_user
)
from .gsettings_applier import (
    gsettings_applier,
    gsettings_applier_user
)
from util.windows import get_sid
from util.users import (
    is_root,
    get_process_user,
    username_match_uid,
    with_privileges
)
from util.logging import slogm

import logging

def determine_username(username=None):
    '''
    Checks if the specified username is valid in order to prevent
    unauthorized operations.
    '''
    name = username

    # If username is not set then it will be the name
    # of process owner.
    if not username:
        name = get_process_user()
        logging.debug(slogm('Username is not specified - will use username of current process'))

    if not username_match_uid(name):
        if not is_root():
            raise Exception('Current process UID does not match specified username')

    logging.debug(slogm('Username for frontend is set to {}'.format(name)))

    return name

class frontend_manager:
    '''
    The frontend_manager class decides when and how to run appliers
    for machine and user parts of policies.
    '''

    def __init__(self, username, target):
        self.storage = registry_factory('registry')
        self.username = determine_username(username)
        self.target = target
        self.process_uname = get_process_user()
        self.sid = get_sid(self.storage.get_info('domain'), self.username)

        self.machine_appliers = dict({
            'control':  control_applier(self.storage),
            'polkit':   polkit_applier(self.storage),
            'systemd':  systemd_applier(self.storage),
            'firefox':  firefox_applier(self.storage, self.sid, self.username),
            'chromium': chromium_applier(self.storage, self.sid, self.username),
            'shortcuts': shortcut_applier(self.storage),
            'gsettings': gsettings_applier(self.storage),
            'cups': cups_applier(self.storage),
            'package': package_applier(self.storage)
        })

        # User appliers are expected to work with user-writable
        # files and settings, mostly in $HOME.
        self.user_appliers = dict({
            'shortcuts': shortcut_applier_user(self.storage, self.sid, self.username),
            'gsettings': gsettings_applier_user(self.storage, self.sid, self.username)
        })

    def machine_apply(self):
        '''
        Run global appliers with administrator privileges.
        '''
        if not is_root():
            logging.error('Not sufficient privileges to run machine appliers')
            return
        logging.debug(slogm('Applying computer part of settings'))
        self.machine_appliers['systemd'].apply()
        self.machine_appliers['control'].apply()
        self.machine_appliers['polkit'].apply()
        self.machine_appliers['firefox'].apply()
        self.machine_appliers['chromium'].apply()
        self.machine_appliers['shortcuts'].apply()
        self.machine_appliers['gsettings'].apply()
        self.machine_appliers['cups'].apply()
        self.machine_appliers['package'].apply()

    def user_apply(self):
        '''
        Run appliers for users.
        '''
        if is_root():
            logging.debug(slogm('Running user appliers from administrator context'))
            self.user_appliers['shortcuts'].admin_context_apply()
            self.user_appliers['gsettings'].admin_context_apply()

            logging.debug(slogm('Running user appliers for user context'))
            with_privileges(self.username, self.user_appliers['shortcuts'].user_context_apply)
            with_privileges(self.username, self.user_appliers['gsettings'].user_context_apply)
        else:
            logging.debug(slogm('Running user appliers from user context'))
            self.user_appliers['shortcuts'].user_context_apply()
            self.user_appliers['gsettings'].user_context_apply()

    def apply_parameters(self):
        '''
        Decide which appliers to run.
        '''
        if 'All' == self.target or 'Computer' == self.target:
            self.machine_apply()

        # Run user appliers when user's SID is specified
        if self.storage.get_info('machine_sid') != self.sid:
            if 'All' == self.target or 'User' == self.target:
                self.user_apply()

