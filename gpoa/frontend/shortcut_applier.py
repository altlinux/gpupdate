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

import subprocess
import shutil

from gpt.shortcuts import get_ttype, shortcut
from util.logging import log
from util.util import get_homedir, homedir_exists, string_to_literal_eval
from util.windows import expand_windows_var
from pathlib import Path

from .applier_frontend import applier_frontend, check_enabled


def storage_get_shortcuts(storage, username=None, shortcuts_machine=None):
    '''
    Query storage for shortcuts' rows for username.
    '''
    shortcut_objs = storage.get_shortcuts()
    shortcuts = []
    if username and shortcuts_machine:
        shortcut_objs += shortcuts_machine

    for sc in shortcut_objs:
        if username:
            sc.set_expanded_path(expand_windows_var(sc.path, username))
        shortcuts.append(sc)

    return shortcuts

def apply_shortcut(shortcut, username=None):
    '''
    Apply the single shortcut file to the disk.

    :username: None means working with machine variables and paths
    '''
    dest_abspath = shortcut.dest
    if not dest_abspath.startswith('/') and not dest_abspath.startswith('%'):
        dest_abspath = '%HOME%/' + dest_abspath
    logdata = {'shortcut': dest_abspath, 'for': username}
    log('D105', logdata)
    dest_abspath = expand_windows_var(dest_abspath, username).replace('\\', '/') + '.desktop'

    # Check that we're working for user, not on global system level
    if username:
        # Check that link destination path starts with specification of
        # user's home directory
        if dest_abspath.startswith(get_homedir(username)):
            # Don't try to operate on non-existent directory
            if not homedir_exists(username):
                logdata = {'user': username, 'dest_abspath': dest_abspath}
                log('W7', logdata)
                return None
        else:
            logdata = {'user': username, 'bad path': dest_abspath}
            log('W8', logdata)
            return None

    if '%' in dest_abspath:
        logdata = {'dest_abspath': dest_abspath}
        log('E53', logdata)
        return None

    if not dest_abspath.startswith('/'):
        logdata = {'dest_abspath': dest_abspath}
        log('E54', logdata)
        return None
    logdata = {'file': dest_abspath}
    logdata['with_action'] = shortcut.action
    log('D106', logdata)
    shortcut.apply_desktop(dest_abspath)

    try:
        if getattr(shortcut, 'action', None) in ('C', 'U', 'R'):
            if Path(dest_abspath).exists() and shutil.which('gio'):
                user_home = get_homedir(username) if username else None
                if username and user_home and dest_abspath.startswith(user_home.rstrip('/') + '/'):
                    command = ['gio', 'set', dest_abspath, 'metadata::trusted', 'true']
                    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
                    gio_out = (result.stderr or result.stdout or '').strip()
                    logdata = {'command': command, 'gio_out': gio_out}
                    if result.returncode != 0:
                        log('D238', logdata)
                    else:
                        log('D239', logdata)
    except Exception as e:
        log('E81', logdata)


class shortcut_applier(applier_frontend):
    __module_name = 'ShortcutsApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage):
        self.storage = storage
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        shortcuts = storage_get_shortcuts(self.storage)
        if shortcuts:
            for sc in shortcuts:
                apply_shortcut(sc)
            if len(shortcuts) > 0:
                # According to ArchWiki - this thing is needed to rebuild MIME
                # type cache in order file bindings to work. This rebuilds
                # databases located in /usr/share/applications and
                # /usr/local/share/applications
                subprocess.check_call(['/usr/bin/update-desktop-database'])
        else:
            log('D100')

    def apply(self):
        if self.__module_enabled:
            log('D98')
            self.run()
        else:
            log('D99')

class shortcut_applier_user(applier_frontend):
    __module_name = 'ShortcutsApplierUser'
    __module_experimental = False
    __module_enabled = True
    __REGISTRY_PATH_SHORTCATSMERGE= '/Software/BaseALT/Policies/GPUpdate/ShortcutsMerge'
    __DCONF_REGISTRY_PATH_PREFERENCES_MACHINE = 'Software/BaseALT/Policies/Preferences/Machine'

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def get_machine_shortcuts(self):
        result = []
        try:
            storage_machine_dict =  self.storage.get_dictionary_from_dconf_file_db()
            machine_shortcuts = storage_machine_dict.get(
                self.__DCONF_REGISTRY_PATH_PREFERENCES_MACHINE, dict()).get('Shortcuts')
            shortcut_objs =  string_to_literal_eval(machine_shortcuts)
            for obj in shortcut_objs:
                shortcut_machine =shortcut(
                    obj.get('dest'),
                    obj.get('path'),
                    obj.get('arguments'),
                    obj.get('name'),
                    obj.get('action'),
                    get_ttype(obj.get('target_type')))
                shortcut_machine.set_usercontext(1)
                result.append(shortcut_machine)
        except:
            return None
        return result



    def check_enabled_shortcuts_merge(self):
        return self.storage.get_key_value(self.__REGISTRY_PATH_SHORTCATSMERGE)

    def run(self, in_usercontext):
        shortcuts_machine = None
        if self.check_enabled_shortcuts_merge():
            shortcuts_machine = self.get_machine_shortcuts()
        shortcuts = storage_get_shortcuts(self.storage, self.username, shortcuts_machine)

        if shortcuts:
            for sc in shortcuts:
                if in_usercontext and sc.is_usercontext():
                    apply_shortcut(sc, self.username)
                if not in_usercontext and not sc.is_usercontext():
                    apply_shortcut(sc, self.username)
        else:
            logdata = {'username': self.username}
            log('D100', logdata)

    def user_context_apply(self):
        if self.__module_enabled:
            log('D101')
            self.run(True)
        else:
            log('D102')

    def admin_context_apply(self):
        if self.__module_enabled:
            log('D103')
            self.run(False)
        else:
            log('D104')

