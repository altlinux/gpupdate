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
import shutil
from pathlib import Path
import pysss_nss_idmap

from django.template import base
from util.logging import log
from .appliers.folder import remove_dir_tree
from .applier_frontend import (
      applier_frontend
    , check_enabled
)

class scripts_applier(applier_frontend):
    __module_name = 'ScriptsApplier'
    __module_experimental = False
    __module_enabled = True
    __cache_scripts = '/var/cache/gpupdate_scripts_cache/machine/'

    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.scripts = self.storage.get_scripts(self.sid)
        self.folder_path = Path(self.__cache_scripts)
        machine_name = os.uname()[1] + '$'
        check_sid =  pysss_nss_idmap.getsidbyname(machine_name)
        self.__module_enabled = check_enabled(self.storage
            , self.__module_name
            , self.__module_experimental
        )
        if sid in check_sid[machine_name]['sid']:
            try:
                remove_dir_tree(self.folder_path, True, True, True,)
            except FileNotFoundError as exc:
                log('D153')
            except Exception as exc:
                logdata = dict()
                logdata['exc'] = exc
                log('E63', logdata)
            self.folder_path.mkdir(parents=True, exist_ok=True)
            if self.__module_enabled:
                for ts in self.scripts:
                    if ts.path.split('/')[-4] == 'MACHINE':
                        script_path = (self.__cache_scripts +
                                       ts.policy_num + '/' +
                                       '/'.join(ts.path.split('/')[ts.path.split('/').index('POLICIES')+4:-1]))
                        install_script(ts, script_path, '700')

    def run(self):
        pass
    def apply(self):
        pass

class scripts_applier_user(applier_frontend):
    __module_name = 'ScriptsApplierUser'
    __module_experimental = False
    __module_enabled = True
    __cache_scripts = '/var/cache/gpupdate_scripts_cache/users/'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.scripts = self.storage.get_scripts(self.sid)
        self.folder_path = Path(self.__cache_scripts + self.username)
        self.__module_enabled = check_enabled(self.storage
            , self.__module_name
            , self.__module_experimental
        )
        if self.username[:-1] != os.uname()[1].upper():
            try:
                remove_dir_tree(self.folder_path, True, True, True,)
            except FileNotFoundError as exc:
                log('D154')
            except Exception as exc:
                logdata = dict()
                logdata['exc'] = exc
                log('E64', logdata)
            self.folder_path.mkdir(parents=True, exist_ok=True)
            if self.__module_enabled:
                for ts in self.scripts:
                    if ts.path.split('/')[-4] == 'USER':
                        script_path = (self.__cache_scripts +
                                       self.username + '/' +
                                       ts.policy_num + '/' +
                                       '/'.join(ts.path.split('/')[ts.path.split('/').index('POLICIES')+4:-1]))
                        install_script(ts, script_path, '755')


    def user_context_apply(self):
        pass
    def run(self):
        pass

    def admin_context_apply(self):
        '''
        Install software assigned to specified username regardless
        which computer he uses to log into system.
        '''
        pass

def install_script(storage_script_entry, script_path, access_permissions):
    dir_cr = Path(script_path)
    dir_cr.mkdir(parents=True, exist_ok=True)
    script_file = (script_path + '/' +
                   str(int(storage_script_entry.queue)).zfill(5) +
                   '_' + storage_script_entry.path.split('/')[-1])
    shutil.copyfile(storage_script_entry.path, script_file)
    os.chmod(script_file, int(access_permissions, base = 8))
    if storage_script_entry.arg:
        dir_path = script_path + '/' + script_file.split('/')[-1] + '.arg'
        dir_arg = Path(dir_path)
        dir_arg.mkdir(parents=True, exist_ok=True)
        file_arg = open(dir_path + '/arg', 'w')
        file_arg.write(storage_script_entry.arg)
        file_arg.close()
