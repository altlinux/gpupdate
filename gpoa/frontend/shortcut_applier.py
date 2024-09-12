#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.windows import expand_windows_var
from util.logging import log
from util.util import (
        get_homedir,
        homedir_exists
)

def storage_get_shortcuts(storage, sid, username=None):
    '''
    Query storage for shortcuts' rows for specified SID.
    '''
    shortcut_objs = storage.get_shortcuts(sid)
    shortcuts = list()

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
    logdata = dict()
    logdata['shortcut'] = dest_abspath
    logdata['for'] = username
    log('D105', logdata)
    dest_abspath = expand_windows_var(dest_abspath, username).replace('\\', '/') + '.desktop'

    # Check that we're working for user, not on global system level
    if username:
        # Check that link destination path starts with specification of
        # user's home directory
        if dest_abspath.startswith(get_homedir(username)):
            # Don't try to operate on non-existent directory
            if not homedir_exists(username):
                logdata = dict()
                logdata['user'] = username
                logdata['dest_abspath'] = dest_abspath
                log('W7', logdata)
                return None
        else:
            logdata = dict()
            logdata['user'] = username
            logdata['bad path'] = dest_abspath
            log('W8', logdata)
            return None

    if '%' in dest_abspath:
        logdata = dict()
        logdata['dest_abspath'] = dest_abspath
        log('E53', logdata)
        return None

    if not dest_abspath.startswith('/'):
        logdata = dict()
        logdata['dest_abspath'] = dest_abspath
        log('E54', logdata)
        return None
    logdata = dict()
    logdata['file'] = dest_abspath
    logdata['with_action'] = shortcut.action
    log('D106', logdata)
    shortcut.apply_desktop(dest_abspath)

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
        shortcuts = storage_get_shortcuts(self.storage, self.storage.get_info('machine_sid'))
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
            logdata = dict()
            logdata['machine_sid'] = self.storage.get_info('machine_sid')
            log('D100', logdata)

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

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def run(self, in_usercontext):
        shortcuts = storage_get_shortcuts(self.storage, self.sid, self.username)

        if shortcuts:
            for sc in shortcuts:
                if in_usercontext and sc.is_usercontext():
                    apply_shortcut(sc, self.username)
                if not in_usercontext and not sc.is_usercontext():
                    apply_shortcut(sc, self.username)
        else:
            logdata = dict()
            logdata['sid'] = self.sid
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

