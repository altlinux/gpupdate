#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from storage import registry_factory
from storage.fs_file_cache import fs_file_cache

from .control_applier import control_applier
from .polkit_applier import (
      polkit_applier
    , polkit_applier_user
)
from .systemd_applier import systemd_applier
from .firefox_applier import firefox_applier
from .thunderbird_applier import thunderbird_applier
from .chromium_applier import chromium_applier
from .cups_applier import cups_applier
from .package_applier import (
      package_applier
    , package_applier_user
)
from .shortcut_applier import (
    shortcut_applier,
    shortcut_applier_user
)
from .gsettings_applier import (
    gsettings_applier,
    gsettings_applier_user
)
from .firewall_applier import firewall_applier
from .folder_applier import (
      folder_applier
    , folder_applier_user
)
from .cifs_applier import (
      cifs_applier_user
    , cifs_applier)
from .ntp_applier import ntp_applier
from .envvar_applier import (
      envvar_applier
    , envvar_applier_user
)
from .scripts_applier import (
      scripts_applier
    , scripts_applier_user
)

from .file_applier import (
      file_applier
    , file_applier_user
)

from .ini_applier import (
      ini_applier
    , ini_applier_user
)

from .kde_applier import (
      kde_applier
    , kde_applier_user
)
from .laps_applier import laps_applier

from .networkshare_applier import networkshare_applier
from .yandex_browser_applier import yandex_browser_applier

from util.users import (
    is_root,
    get_process_user,
    username_match_uid,
)
from util.logging import log
from util.system import with_privileges


def determine_username(username=None):
    '''
    Checks if the specified username is valid in order to prevent
    unauthorized operations.
    '''
    name = username

    # If username is not set then it will be the name
    # of process owner.
    logdata = {'username': name}
    if not username:
        name = get_process_user()
        log('D2', logdata)

    if not username_match_uid(name):
        if not is_root():
            raise Exception('Current process UID does not match specified username')

    log('D15', logdata)

    return name

def apply_user_context(user_appliers):
    for applier_name, applier_object in user_appliers.items():
        log('D55', {'name': applier_name})

        try:
            applier_object.user_context_apply()
        except Exception as exc:
            logdata = {'applier': applier_name, 'exception': str(exc)}
            log('E20', logdata)

class frontend_manager:
    '''
    The frontend_manager class decides when and how to run appliers
    for machine and user parts of policies.
    '''

    def __init__(self, username, is_machine):
        self.username = determine_username(username)
        self.storage = registry_factory('dconf', username=self.username)
        self.is_machine = is_machine
        self.process_uname = get_process_user()
        self.file_cache = fs_file_cache('file_cache', self.username)

        self.machine_appliers = dict()
        self.user_appliers = dict()
        if is_machine:
            self._init_machine_appliers()
        else:
            self._init_user_appliers()

    def _init_machine_appliers(self):
        self.machine_appliers['laps_applier'] = laps_applier(self.storage)
        self.machine_appliers['control'] = control_applier(self.storage)
        self.machine_appliers['polkit'] = polkit_applier(self.storage)
        self.machine_appliers['systemd'] = systemd_applier(self.storage)
        self.machine_appliers['firefox'] = firefox_applier(self.storage, self.username)
        self.machine_appliers['thunderbird'] = thunderbird_applier(self.storage, self.username)
        self.machine_appliers['chromium'] = chromium_applier(self.storage, self.username)
        self.machine_appliers['yandex_browser'] = yandex_browser_applier(self.storage, self.username)
        self.machine_appliers['shortcuts'] = shortcut_applier(self.storage)
        self.machine_appliers['gsettings'] = gsettings_applier(self.storage, self.file_cache)
        try:
            self.machine_appliers['cifs'] = cifs_applier(self.storage)
        except Exception as exc:
            logdata = {'applier_name': 'cifs', 'msg': str(exc)}
            log('E24', logdata)
        self.machine_appliers['cups'] = cups_applier(self.storage)
        self.machine_appliers['firewall'] = firewall_applier(self.storage)
        self.machine_appliers['folders'] = folder_applier(self.storage)
        self.machine_appliers['ntp'] = ntp_applier(self.storage)
        self.machine_appliers['envvar'] = envvar_applier(self.storage)
        self.machine_appliers['networkshare'] = networkshare_applier(self.storage)
        self.machine_appliers['scripts'] = scripts_applier(self.storage)
        self.machine_appliers['files'] = file_applier(self.storage, self.file_cache)
        self.machine_appliers['ini'] = ini_applier(self.storage)
        self.machine_appliers['kde'] = kde_applier(self.storage)
        self.machine_appliers['package'] = package_applier(self.storage)

    def _init_user_appliers(self):
        # User appliers are expected to work with user-writable
        # files and settings, mostly in $HOME.
        self.user_appliers['shortcuts'] = shortcut_applier_user(self.storage, self.username)
        self.user_appliers['folders'] = folder_applier_user(self.storage, self.username)
        self.user_appliers['gsettings'] = gsettings_applier_user(self.storage, self.file_cache, self.username)
        try:
            self.user_appliers['cifs'] = cifs_applier_user(self.storage, self.username)
        except Exception as exc:
            logdata = {'applier_name': 'cifs', 'msg': str(exc)}
            log('E25', logdata)
        self.user_appliers['polkit'] = polkit_applier_user(self.storage, self.username)
        self.user_appliers['envvar'] = envvar_applier_user(self.storage, self.username)
        self.user_appliers['networkshare'] = networkshare_applier(self.storage, self.username)
        self.user_appliers['scripts'] = scripts_applier_user(self.storage, self.username)
        self.user_appliers['files'] = file_applier_user(self.storage, self.file_cache, self.username)
        self.user_appliers['ini'] = ini_applier_user(self.storage, self.username)
        self.user_appliers['kde'] = kde_applier_user(self.storage, self.username, self.file_cache)
        self.user_appliers['package'] = package_applier_user(self.storage, self.username)

    def machine_apply(self):
        '''
        Run global appliers with administrator privileges.
        '''
        if not is_root():
            log('E13')
            return
        log('D16')

        for applier_name, applier_object in self.machine_appliers.items():
            try:
                applier_object.apply()
            except Exception as exc:
                logdata = {'applier_name': applier_name, 'msg': str(exc)}
                log('E24', logdata)

    def user_apply(self):
        '''
        Run appliers for users.
        '''
        if is_root():
            for applier_name, applier_object in self.user_appliers.items():
                try:
                    applier_object.admin_context_apply()
                except Exception as exc:
                    logdata = {'applier': applier_name, 'exception': str(exc)}
                    log('E19', logdata)

            try:
                with_privileges(self.username, lambda: apply_user_context(self.user_appliers))
            except Exception as exc:
                logdata = {'username': self.username, 'exception': str(exc)}
                log('E30', logdata)
        else:
            for applier_name, applier_object in self.user_appliers.items():
                try:
                    applier_object.user_context_apply()
                except Exception as exc:
                    logdata = {'applier_name': applier_name, 'message': str(exc)}
                    log('E11', logdata)

    def apply_parameters(self):
        '''
        Decide which appliers to run.
        '''
        if self.is_machine:
            self.machine_apply()
        else:
            self.user_apply()

