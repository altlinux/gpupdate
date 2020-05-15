#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
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

import logging
import subprocess

from .applier_frontend import applier_frontend
from gpt.shortcuts import json2sc
from util.windows import expand_windows_var
from util.logging import slogm
from util.util import (
        get_homedir,
        homedir_exists
)

def storage_get_shortcuts(storage, sid):
    '''
    Query storage for shortcuts' rows for specified SID.
    '''
    shortcut_objs = storage.get_shortcuts(sid)
    shortcuts = list()

    for sc_obj in shortcut_objs:
        sc = json2sc(sc_obj.shortcut)
        shortcuts.append(sc)

    return shortcuts

def write_shortcut(shortcut, username=None):
    '''
    Write the single shortcut file to the disk.

    :username: None means working with machine variables and paths
    '''
    dest_abspath = shortcut.dest
    if not dest_abspath.startswith('/') and not dest_abspath.startswith('%'):
        dest_abspath = '%HOME%/' + dest_abspath

    logging.debug(slogm('Try to expand path for shortcut: {} for {}'.format(dest_abspath, username)))
    dest_abspath = expand_windows_var(dest_abspath, username).replace('\\', '/') + '.desktop'

    # Check that we're working for user, not on global system level
    if username:
        # Check that link destination path starts with specification of
        # user's home directory
        if dest_abspath.startswith(get_homedir(username)):
            # Don't try to operate on non-existent directory
            if not homedir_exists(username):
                logging.warning(slogm('No home directory exists for user {}: will not create link {}'.format(username, dest_abspath)))
                return None
        else:
            logging.warning(slogm('User\'s shortcut not placed to home directory for {}: bad path {}'.format(username, dest_abspath)))
            return None

    if '%' in dest_abspath:
        logging.debug(slogm('Fail for writing shortcut to file with \'%\': {}'.format(dest_abspath)))
        return None

    if not dest_abspath.startswith('/'):
        logging.debug(slogm('Fail for writing shortcut to not absolute path \'%\': {}'.format(dest_abspath)))
        return None

    logging.debug(slogm('Writing shortcut file to {}'.format(dest_abspath)))
    shortcut.write_desktop(dest_abspath)

class shortcut_applier(applier_frontend):
    def __init__(self, storage):
        self.storage = storage

    def apply(self):
        shortcuts = storage_get_shortcuts(self.storage, self.storage.get_info('machine_sid'))
        if shortcuts:
            for sc in shortcuts:
                write_shortcut(sc)
        else:
            logging.debug(slogm('No shortcuts to process for {}'.format(self.storage.get_info('machine_sid'))))
        # According to ArchWiki - this thing is needed to rebuild MIME
        # type cache in order file bindings to work. This rebuilds
        # databases located in /usr/share/applications and
        # /usr/local/share/applications
        subprocess.check_call(['/usr/bin/update-desktop-database'])

class shortcut_applier_user(applier_frontend):
    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

    def user_context_apply(self):
        shortcuts = storage_get_shortcuts(self.storage, self.sid)

        if shortcuts:
            for sc in shortcuts:
                if sc.is_usercontext():
                    write_shortcut(sc, self.username)
        else:
            logging.debug(slogm('No shortcuts to process for {}'.format(self.sid)))

    def admin_context_apply(self):
        shortcuts = storage_get_shortcuts(self.storage, self.sid)

        if shortcuts:
            for sc in shortcuts:
                if not sc.is_usercontext():
                    write_shortcut(sc, self.username)
        else:
            logging.debug(slogm('No shortcuts to process for {}'.format(self.sid)))

