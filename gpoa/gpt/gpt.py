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
from .scriptsini import (
      read_scripts
    , merge_scripts
)
import util
import util.preg
from util.paths import (
    local_policy_path,
    cache_dir,
    local_policy_cache,
    local_policy_admin_path
)
from util.logging import log


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
    SCRIPTS = 'scripts.ini'

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
    parsers[FileType.SCRIPTS] = read_scripts

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
    mergers[FileType.SCRIPTS] = merge_scripts

    return mergers

def get_merger(preference_type):
    mergers = pref_mergers()
    return mergers[preference_type]

class gpt:
    def __init__(self, gpt_path, sid):
        self.path = gpt_path
        self.sid = sid
        self.storage = registry_factory('registry')
        self.name = ''
        self.guid = self.path.rpartition('/')[2]
        if 'default' == self.guid:
            self.guid = 'Local Policy'

        self._machine_path = find_dir(self.path, 'Machine')
        self._user_path = find_dir(self.path, 'User')
        self._scripts_machine_path = find_dir(self._machine_path, 'Scripts')
        self._scripts_user_path = find_dir(self._user_path, 'Scripts')

        self.settings_list = [
              'shortcuts'
            , 'drives'
            , 'environmentvariables'
            , 'printers'
            , 'folders'
            , 'files'
            , 'inifiles'
            , 'services'
            , 'scheduledtasks'
            , 'scripts'
        ]
        self.settings = dict()
        self.settings['machine'] = dict()
        self.settings['user'] = dict()
        self.settings['machine']['regpol'] = find_file(self._machine_path, 'registry.pol')
        self.settings['user']['regpol'] = find_file(self._user_path, 'registry.pol')
        for setting in self.settings_list:
            machine_preffile = find_preffile(self._machine_path, setting)
            user_preffile = find_preffile(self._user_path, setting)
            mlogdata = dict({'setting': setting, 'prefpath': machine_preffile})
            log('D24', mlogdata)
            self.settings['machine'][setting] = machine_preffile
            ulogdata = dict({'setting': setting, 'prefpath': user_preffile})
            log('D23', ulogdata)
            self.settings['user'][setting] = user_preffile

        self.settings['machine']['scripts'] = find_file(self._scripts_machine_path, 'scripts.ini')
        self.settings['user']['scripts'] = find_file(self._scripts_user_path, 'scripts.ini')


    def set_name(self, name):
        '''
        Set human-readable GPT name.
        '''
        self.name = name

    def merge_machine(self):
        '''
        Merge machine settings to storage.
        '''
        try:
            # Merge machine policies to registry if possible
            if self.settings['machine']['regpol']:
                mlogdata = dict({'polfile': self.settings['machine']['regpol']})
                log('D34', mlogdata)
                util.preg.merge_polfile(self.settings['machine']['regpol'], policy_name=self.name)
            # Merge machine preferences to registry if possible
            for preference_name, preference_path in self.settings['machine'].items():
                if preference_path:
                    preference_type = get_preftype(preference_path)
                    logdata = dict({'pref': preference_type.value, 'sid': self.sid})
                    log('D28', logdata)
                    preference_parser = get_parser(preference_type)
                    preference_merger = get_merger(preference_type)
                    preference_objects = preference_parser(preference_path)
                    preference_merger(self.storage, self.sid, preference_objects, self.name)
        except Exception as exc:
            logdata = dict()
            logdata['gpt'] = self.name
            logdata['msg'] = str(exc)
            log('E28', logdata)

    def merge_user(self):
        '''
        Merge user settings to storage.
        '''
        try:
            # Merge user policies to registry if possible
            if self.settings['user']['regpol']:
                mulogdata = dict({'polfile': self.settings['user']['regpol']})
                log('D35', mulogdata)
                util.preg.merge_polfile(self.settings['user']['regpol'], sid=self.sid, policy_name=self.name)
            # Merge user preferences to registry if possible
            for preference_name, preference_path in self.settings['user'].items():
                if preference_path:
                    preference_type = get_preftype(preference_path)
                    logdata = dict({'pref': preference_type.value, 'sid': self.sid})
                    log('D29', logdata)
                    preference_parser = get_parser(preference_type)
                    preference_merger = get_merger(preference_type)
                    preference_objects = preference_parser(preference_path)
                    preference_merger(self.storage, self.sid, preference_objects, self.name)
        except Exception as exc:
            logdata = dict()
            logdata['gpt'] = self.name
            logdata['msg'] = str(exc)
            log('E29', logdata)

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
    lppath = os.path.join(local_policy_path(), 'Machine/Registry.pol.xml')

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
    log('D25')
    lp2gpt()
    local_policy = gpt(str(local_policy_cache()), sid)
    local_policy.set_name('Local Policy')

    return local_policy

def get_local_admin_gpt(sid):
    '''
    Create object out of local_admin_gpt.
    '''
    try:
        path_lp = local_policy_admin_path()
        logdata = dict()
        logdata['path'] = path_lp
        log('D162', logdata)
        local_admin_policy = gpt(path_lp, sid)
        local_admin_policy.set_name('Alt local administrator policy')
    except Exception as exc:
        logdata = dict()
        logdata['exc'] = exc
        log('D163', logdata)
        return None
    return local_admin_policy