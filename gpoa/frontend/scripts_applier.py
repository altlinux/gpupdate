#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2022 BaseALT Ltd.
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
import shutil
from pathlib import Path

from util.logging import log
from .appliers.folder import remove_dir_tree
from .applier_frontend import (
      applier_frontend
    , check_enabled
)

class scripts_applier(applier_frontend):
    __module_name = 'ScriptsApplier'
    __module_experimental = True
    __module_enabled = False
    __cache_scripts = '/var/cache/gpupdate_scripts_cache/machine/'

    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.startup_scripts = self.storage.get_scripts(self.sid, 'STARTUP')
        self.shutdown_scripts = self.storage.get_scripts(self.sid, 'SHUTDOWN')
        self.folder_path = Path(self.__cache_scripts)
        self.__module_enabled = check_enabled(self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def cleaning_cache(self):
        log('D160')
        try:
            remove_dir_tree(self.folder_path, True, True, True,)
        except FileNotFoundError as exc:
            log('D154')
        except Exception as exc:
            logdata = dict()
            logdata['exc'] = exc
            log('E64', logdata)

    def filling_cache(self):
        '''
        Creating and updating folder directories for scripts and copying them
        '''
        self.folder_path.mkdir(parents=True, exist_ok=True)
        for ts in self.startup_scripts:
            script_path = os.path.join(self.__cache_scripts, 'STARTUP')
            install_script(ts, script_path, '700')
        for ts in self.shutdown_scripts:
            script_path = os.path.join(self.__cache_scripts, 'SHUTDOWN')
            install_script(ts, script_path, '700')

    def run(self):
        self.filling_cache()

    def apply(self):
        self.cleaning_cache()
        if self.__module_enabled:
            log('D156')
            self.run()
        else:
            log('D157')

class scripts_applier_user(applier_frontend):
    __module_name = 'ScriptsApplierUser'
    __module_experimental = True
    __module_enabled = False
    __cache_scripts = '/var/cache/gpupdate_scripts_cache/users/'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.logon_scripts = self.storage.get_scripts(self.sid, 'LOGON')
        self.logoff_scripts = self.storage.get_scripts(self.sid, 'LOGOFF')
        self.username = username
        self.folder_path = Path(self.__cache_scripts + self.username)
        self.__module_enabled = check_enabled(self.storage
            , self.__module_name
            , self.__module_experimental
        )
        self.filling_cache()

    def cleaning_cache(self):
        log('D161')
        try:
            remove_dir_tree(self.folder_path, True, True, True,)
        except FileNotFoundError as exc:
            log('D155')
        except Exception as exc:
            logdata = dict()
            logdata['exc'] = exc
            log('E65', logdata)

    def filling_cache(self):
        '''
        Creating and updating folder directories for scripts and copying them
        '''
        self.folder_path.mkdir(parents=True, exist_ok=True)

        for ts in self.logon_scripts:
            script_path = os.path.join(self.__cache_scripts, self.username, 'LOGON')
            install_script(ts, script_path, '755')
        for ts in self.logoff_scripts:
            script_path = os.path.join(self.__cache_scripts, self.username, 'LOGOFF')
            install_script(ts, script_path, '755')

    def user_context_apply(self):
        pass

    def run(self):
        self.filling_cache()

    def admin_context_apply(self):
        self.cleaning_cache()
        if self.__module_enabled:
            log('D158')
            self.run()
        else:
            log('D159')

def install_script(storage_script_entry, script_dir, access_permissions):
    '''
    Copy scripts to specific directories and
    if given arguments
    create directories for them and copy them there
    '''
    dir_cr = Path(script_dir)
    dir_cr.mkdir(parents=True, exist_ok=True)
    script_name = str(int(storage_script_entry.number)).zfill(5) + '_' + os.path.basename(storage_script_entry.path)
    script_file = os.path.join(script_dir, script_name)
    shutil.copyfile(storage_script_entry.path, script_file)

    os.chmod(script_file, int(access_permissions, base = 8))
    if storage_script_entry.args:
        dir_path = script_dir + '/' + script_name + '.arg'
        dir_arg = Path(dir_path)
        dir_arg.mkdir(parents=True, exist_ok=True)
        file_arg = open(dir_path + '/arg', 'w')
        file_arg.write(storage_script_entry.args)
        file_arg.close()
