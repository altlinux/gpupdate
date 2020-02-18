#
# Copyright (C) 2019-2020 BaseALT Ltd.
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

import logging
import os

from samba.gp_parse.gp_pol import GPPolParser

from storage import registry_factory
from .shortcuts import read_shortcuts
from .services import read_services
from .printers import read_printers
from .inifiles import read_inifiles
from .folders import read_folders
from .files import read_files
from .envvars import read_envvars
from .drives import read_drives
import util
import util.preg
from util.paths import (
    default_policy_path,
    cache_dir,
    local_policy_cache
)
from util.logging import slogm

class gpt:
    __user_policy_mode_key = 'Software\\Policies\\Microsoft\\Windows\\System\\UserPolicyMode'

    def __init__(self, gpt_path, sid):
        self.path = gpt_path
        self.sid = sid
        self.storage = registry_factory('registry')
        self._scan_gpt()

    def _scan_gpt(self):
        '''
        Collect the data from the specified GPT on file system (cached
        by Samba).
        '''
        self.guid = self.path.rpartition('/')[2]
        self.name = ''
        if 'default' == self.guid:
            self.guid = 'Local Policy'

        self._machine_path = None
        self._user_path = None
        self._get_machine_user_dirs()

        logging.debug(slogm('Looking for machine part of GPT {}'.format(self.guid)))
        self._find_machine()
        logging.debug(slogm('Looking for user part of GPT {}'.format(self.guid)))
        self._find_user()

    def set_name(self, name):
        '''
        Set human-readable GPT name.
        '''
        self.name = name

    def get_policy_mode(self):
        '''
        Get UserPolicyMode parameter value in order to determine if it
        is possible to work with user's part of GPT. This value is
        checked only if working for user's SID.
        '''
        upm = self.storage.get_hklm_entry(self.__user_policy_mode_key)
        if not upm:
            upm = 0
        upm = int(upm)
        if 0 > upm or 2 > upm:
            upm = 0

        return upm

    def _get_machine_user_dirs(self):
        '''
        Find full path to Machine and User parts of GPT.
        '''
        entries = os.listdir(self.path)
        for entry in entries:
            full_entry_path = os.path.join(self.path, entry)
            if os.path.isdir(full_entry_path):
                if 'machine' == entry.lower():
                    self._machine_path = full_entry_path
                if 'user' == entry.lower():
                    self._user_path = full_entry_path

    def _find_user(self):
        self._user_regpol = self._find_regpol('user')
        self._user_shortcuts = self._find_shortcuts('user')

    def _find_machine(self):
        self._machine_regpol = self._find_regpol('machine')
        self._machine_shortcuts = self._find_shortcuts('machine')

    def _find_regpol(self, part):
        '''
        Find Registry.pol files.
        '''
        search_path = self._machine_path
        if 'user' == part:
            search_path = self._user_path
        if not search_path:
            return None

        return find_file(search_path, 'registry.pol')

    def _find_shortcuts(self, part):
        '''
        Find Shortcuts.xml files.
        '''
        search_path = os.path.join(self._machine_path, 'Preferences', 'Shortcuts')
        if 'user' == part:
            try:
                search_path = os.path.join(self._user_path, 'Preferences', 'Shortcuts')
            except Exception as exc:
                return None
        if not search_path:
            return None

        return find_file(search_path, 'shortcuts.xml')

    def _find_envvars(self, part):
        '''
        Find EnvironmentVariables.xml files.
        '''
        search_path = os.path.join(self._machine_path, 'Preferences', 'EnvironmentVariables')
        if 'user' == part:
            search_path = os.path.join(self._user_path, 'Preferences', 'EnvironmentVariables')
        if not search_path:
            return None

        return find_file(search_path, 'environmentvariables.xml')

    def _find_drives(self, part):
        '''
        Find Drives.xml files.
        '''
        search_path = os.path.join(self._machine_path, 'Preferences', 'Drives')
        if 'user' == part:
            search_path = os.path.join(self._user_path, 'Preferences', 'Drives')
        if not search_path:
            return None

        return find_file(search_path, 'drives.xml')

    def _find_printers(self, part):
        '''
        Find Printers.xml files.
        '''
        search_path = os.path.join(self._machine_path, 'Preferences', 'Printers')
        if 'user' == part:
            search_path = os.path.join(self._user_path, 'Preferences', 'Printers')
        if not search_path:
            return None

        return find_file(search_path, 'printers.xml')

    def _merge_shortcuts(self):
        shortcuts = list()

        if self.sid == self.storage.get_info('machine_sid'):
            shortcuts = read_shortcuts(self._machine_shortcuts)
        else:
            shortcuts = read_shortcuts(self._user_shortcuts)

        for sc in shortcuts:
            self.storage.add_shortcut(self.sid, sc)

    def merge(self):
        '''
        Merge machine and user (if sid provided) settings to storage.
        '''
        if self.sid == self.storage.get_info('machine_sid'):
            # Merge machine settings to registry if possible
            if self._machine_regpol:
                logging.debug(slogm('Merging machine settings from {}'.format(self._machine_regpol)))
                util.preg.merge_polfile(self._machine_regpol)
            if self._user_regpol:
                logging.debug(slogm('Merging machine(user) settings from {}'.format(self._machine_regpol)))
                util.preg.merge_polfile(self._user_regpol, self.machine_sid)
            if self._machine_shortcuts:
                logging.debug(slogm('Merging machine shortcuts from {}'.format(self._machine_shortcuts)))
                self._merge_shortcuts()
        else:
            # Merge user settings if UserPolicyMode set accordingly
            # and user settings (for HKCU) are exist.
            policy_mode = upm2str(self.get_policy_mode())
            if 'Merge' == policy_mode or 'Not configured' == policy_mode:
                if self._user_regpol:
                    logging.debug(slogm('Merging user settings from {} for {}'.format(self._user_regpol, self.sid)))
                    util.preg.merge_polfile(self._user_regpol, self.sid)
                if self._user_shortcuts:
                    logging.debug(slogm('Merging user shortcuts from {} for {}'.format(self._user_shortcuts, self.sid)))
                    self._merge_shortcuts()

    def __str__(self):
        template = '''
GUID: {}
Name: {}
For SID: {}

Machine part: {}
Machine Registry.pol: {}
Machine Shortcuts.xml: {}

User part: {}
User Registry.pol: {}
User Shortcuts.xml: {}

'''
        result = template.format(
            self.guid,
            self.name,
            self.sid,

            self._machine_path,
            self._machine_regpol,
            self._machine_shortcuts,

            self._user_path,
            self._user_regpol,
            self._user_shortcuts,
        )
        return result

def find_dir(search_path, name):
    '''
    Attempt for case-insensitive search of directory

    :param search_path: Path to get file list from
    :param name: Name of the directory to search for
    '''
    if not search_path:
        return None

    try:
        file_list = os.listdir(search_path)
        for entry in file_list:
            dir_path = os.path.join(search_path, entry)
            if os.path.isdir(file_path) and name.lower() == entry.lower():
                return dir_path
    except Exception as exc:
        pass

    return None

def find_file(search_path, name):
    '''
    Attempt for case-insensitive file search in directory.
    '''
    if not search_path:
        return None

    if not name:
        return None

    try:
        file_list = os.listdir(search_path)
        for entry in file_list:
            file_path = os.path.join(search_path, entry)
            if os.path.isfile(file_path) and name.lower() == entry.lower():
                return file_path
    except Exception as exc:
        #logging.error(exc)
        pass

    return None

def lp2gpt():
    '''
    Convert local-policy to full-featured GPT.
    '''
    lppath = os.path.join(default_policy_path(), 'local.xml')

    # Load settings from XML PolFile
    polparser = GPPolParser()
    polfile = util.preg.load_preg(lppath)
    polparser.pol_file = polfile

    # Create target default policy directory if missing
    destdir = os.path.join(local_policy_cache(), 'Machine')
    os.makedirs(destdir, exist_ok=True)

    # Write PReg
    polparser.write_binary(os.path.join(destdir, 'Registry.pol'))

def get_local_gpt(sid):
    '''
    Convert default policy to GPT and create object out of it.
    '''
    logging.debug(slogm('Re-caching Local Policy'))
    lp2gpt()
    local_policy = gpt(str(local_policy_cache()), sid)
    local_policy.set_name('Local Policy')

    return local_policy

def upm2str(upm_num):
    '''
    Translate UserPolicyMode to string.
    '''
    result = 'Not configured'

    if upm_num in [1, '1']:
        result = 'Replace'

    if upm_num in [2, '2']:
        result = 'Merge'

    return result

