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
import os
from pathlib import Path
from enum import Enum, unique

from samba.gp_parse.gp_pol import GPPolParser

from storage import registry_factory

from .polfile import (
      read_polfile
    , merge_polfile
)
from .shortcuts import (
      read_shortcuts
    , merge_shortcuts
)
from .services import (
      read_services
    , merge_services
)
from .printers import (
      read_printers
    , merge_printers
)
from .inifiles import (
      read_inifiles
    , merge_inifiles
)
from .folders import (
      read_folders
    , merge_folders
)
from .files import (
      read_files
    , merge_files
)
from .envvars import (
      read_envvars
    , merge_envvars
)
from .drives import (
      read_drives
    , merge_drives
)
from .tasks import (
      read_tasks
    , merge_tasks
)

import util
import util.preg
from util.paths import (
    default_policy_path,
    cache_dir,
    local_policy_cache
)
from util.logging import slogm


@unique
class FileType(Enum):
    PREG = 'registry.pol'
    SHORTCUTS = 'shortcuts.xml'
    FOLDERS = 'folders.xml'
    FILES = 'files.xml'
    DRIVES = 'drives.xml'
    SCHEDULEDTASKS = 'scheduledtasks.xml'
    ENVIRONMENTVARIABLES = 'environmentvariables.xml'
    INIFILES = 'inifiles.xml'
    SERVICES = 'services.xml'
    PRINTERS = 'printers.xml'

def get_preftype(path_to_file):
    fpath = Path(path_to_file)

    if fpath.exists():
        file_name = fpath.name.lower()
        for item in FileType:
            if file_name == item.value:
                return item

    return None

def pref_parsers():
    parsers = dict()

    parsers[FileType.PREG] = read_polfile
    parsers[FileType.SHORTCUTS] = read_shortcuts
    parsers[FileType.FOLDERS] = read_folders
    parsers[FileType.FILES] = read_files
    parsers[FileType.DRIVES] = read_drives
    parsers[FileType.SCHEDULEDTASKS] = read_tasks
    parsers[FileType.ENVIRONMENTVARIABLES] = read_envvars
    parsers[FileType.INIFILES] = read_inifiles
    parsers[FileType.SERVICES] = read_services
    parsers[FileType.PRINTERS] = read_printers

    return parsers

def get_parser(preference_type):
    parsers = pref_parsers()
    return parsers[preference_type]

def pref_mergers():
    mergers = dict()

    mergers[FileType.PREG] = merge_polfile
    mergers[FileType.SHORTCUTS] = merge_shortcuts
    mergers[FileType.FOLDERS] = merge_folders
    mergers[FileType.FILES] = merge_files
    mergers[FileType.DRIVES] = merge_drives
    mergers[FileType.SCHEDULEDTASKS] = merge_tasks
    mergers[FileType.ENVIRONMENTVARIABLES] = merge_envvars
    mergers[FileType.INIFILES] = merge_inifiles
    mergers[FileType.SERVICES] = merge_services
    mergers[FileType.PRINTERS] = merge_printers

    return mergers

def get_merger(preference_type):
    mergers = pref_mergers()
    return mergers[preference_type]

class gpt:
    __user_policy_mode_key = 'Software\\Policies\\Microsoft\\Windows\\System\\UserPolicyMode'

    def __init__(self, gpt_path, sid):
        self.path = gpt_path
        self.sid = sid
        self.storage = registry_factory('registry')
        self.name = ''

        self.guid = self.path.rpartition('/')[2]
        self.name = ''
        if 'default' == self.guid:
            self.guid = 'Local Policy'

        self._machine_path = find_dir(self.path, 'Machine')
        self._user_path = find_dir(self.path, 'User')

        self.settings_list = [
              'shortcuts'
            , 'drives'
            , 'environmentvariables'
            #, 'printers'
            , 'folders'
            , 'files'
            , 'inifiles'
            , 'services'
            , 'scheduledtasks'
        ]
        self.settings = dict()
        self.settings['machine'] = dict()
        self.settings['user'] = dict()
        self.settings['machine']['regpol'] = find_file(self._machine_path, 'registry.pol')
        self.settings['user']['regpol'] = find_file(self._user_path, 'registry.pol')
        for setting in self.settings_list:
            machine_preffile = find_preffile(self._machine_path, setting)
            user_preffile = find_preffile(self._user_path, setting)
            logging.debug('Looking for {} in machine part of GPT {}: {}'.format(setting, self.name, machine_preffile))
            self.settings['machine'][setting] = machine_preffile
            logging.debug('Looking for {} in user part of GPT {}: {}'.format(setting, self.name, user_preffile))
            self.settings['user'][setting] = user_preffile

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

    def merge(self):
        '''
        Merge machine and user (if sid provided) settings to storage.
        '''
        if self.sid == self.storage.get_info('machine_sid'):
            # Merge machine settings to registry if possible
            for preference_name, preference_path in self.settings['machine'].items():
                if preference_path:
                    preference_type = get_preftype(preference_path)
                    logstring = 'Reading and merging {} for {}'.format(preference_type.value, self.sid)
                    logging.debug(logstring)
                    preference_parser = get_parser(preference_type)
                    preference_merger = get_merger(preference_type)
                    preference_objects = preference_parser(preference_path)
                    preference_merger(self.storage, self.sid, preference_objects, self.name)
            if self.settings['user']['regpol']:
                logging.debug(slogm('Merging machine(user) settings from {}'.format(self.settings['machine']['regpol'])))
                util.preg.merge_polfile(self.settings['user']['regpol'], sid=self.sid, policy_name=self.name)
            if self.settings['machine']['regpol']:
                logging.debug(slogm('Merging machine settings from {}'.format(self.settings['machine']['regpol'])))
                util.preg.merge_polfile(self.settings['machine']['regpol'], policy_name=self.name)
        else:
            # Merge user settings if UserPolicyMode set accordingly
            # and user settings (for HKCU) are exist.
            policy_mode = upm2str(self.get_policy_mode())
            if 'Merge' == policy_mode or 'Not configured' == policy_mode:
                for preference_name, preference_path in self.settings['user'].items():
                    if preference_path:
                        preference_type = get_preftype(preference_path)
                        logstring = 'Reading and merging {} for {}'.format(preference_type.value, self.sid)
                        logging.debug(logstring)
                        preference_parser = get_parser(preference_type)
                        preference_merger = get_merger(preference_type)
                        preference_objects = preference_parser(preference_path)
                        preference_merger(self.storage, self.sid, preference_objects, self.name)

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
            if os.path.isdir(dir_path) and name.lower() == str(entry).lower():
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
            if os.path.isfile(file_path) and name.lower() == str(entry).lower():
                return file_path
    except Exception as exc:
        #logging.error(exc)
        pass

    return None

def find_preferences(search_path):
    '''
    Find 'Preferences' directory
    '''
    if not search_path:
        return None

    return find_dir(search_path, 'Preferences')

def find_preffile(search_path, prefname):
    '''
    Find file with path like Preferences/prefname/prefname.xml
    '''
    # Look for 'Preferences' directory
    prefdir = find_preferences(search_path)

    if not prefdir:
        return None

    # Then search for preference directory
    pref_dir = find_dir(prefdir, prefname)
    file_name = '{}.xml'.format(prefname)
    # And then try to find the corresponding file.
    pref_file = find_file(pref_dir, file_name)

    return pref_file

def lp2gpt():
    '''
    Convert local-policy to full-featured GPT.
    '''
    lppath = os.path.join(default_policy_path(), 'Machine/Registry.pol.xml')

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

