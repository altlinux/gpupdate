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

import subprocess
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
    __cache_scripts = '/var/cache/gpupdate/cache_scripts_machine/'

    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.scripts = self.storage.get_scripts(self.sid)
        self.folder_path = Path(self.__cache_scripts)
        machine_name = os.uname()[1] + '$'
        check_sid =  pysss_nss_idmap.getsidbyname(machine_name)
        if sid in check_sid[machine_name]['sid']:
            try:
                remove_dir_tree(self.folder_path, True, True, True,)
            except Exception as exc:
                print('FAILED {}'.format(exc))
            self.folder_path.mkdir(parents=True, exist_ok=True)

            for ts in self.scripts:
                if ts.path.split('/')[-4] == 'MACHINE':
                    script_path = (self.__cache_scripts +
                                   ts.policy_num + '/' +
                                   '/'.join(ts.path.split('/')[ts.path.split('/').index('POLICIES')+3:-1]))
                    dir_cr = Path(script_path)
                    dir_cr.mkdir(parents=True, exist_ok=True)


    def run(self):
        pass
    def apply(self):
        self.run()
        #if self.__module_enabled:
            #log('D??')
            #self.run()
        #else:
            #log('D??')

class scripts_applier_user(applier_frontend):
    __module_name = 'ScriptsApplierUser'
    __module_experimental = False
    __module_enabled = True
    __cache_scripts = '/var/cache/gpupdate/cache_scripts_user/'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.scripts = self.storage.get_scripts(self.sid)
        self.folder_path = Path(self.__cache_scripts + self.username)

        if self.username[:-1] != os.uname()[1].upper():
            try:
                remove_dir_tree(self.folder_path, True, True, True,)
            except Exception as exc:
                print('FAILED {}'.format(exc))
            self.folder_path.mkdir(parents=True, exist_ok=True)
            for ts in self.scripts:
                if ts.path.split('/')[-4] == 'USER':
                    script_path = (self.__cache_scripts +
                                   self.username + '/' +
                                   ts.policy_num + '/' +
                                   '/'.join(ts.path.split('/')[ts.path.split('/').index('POLICIES')+3:-1]))
                    dir_cr = Path(script_path)
                    dir_cr.mkdir(parents=True, exist_ok=True)


    def user_context_apply(self):
        pass
    def run(self):
        pass

    def admin_context_apply(self):
        '''
        Install software assigned to specified username regardless
        which computer he uses to log into system.
        '''
        #if self.__module_enabled:
            #log('D??')
            #self.run()
        #else:
            #log('D??')
        pass

