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
from util.logging import slogm, log
from util.rpm import (
      update
    , install_rpm
    , remove_rpm
)

from .applier_frontend import (
      applier_frontend
    , check_enabled
)

class package_applier(applier_frontend):
    __module_name = 'PackagesApplier'
    __module_experimental = True
    __module_enabled = False
    __install_key_name = 'Install'
    __remove_key_name = 'Remove'
    __sync_key_name = 'Sync'
    __hklm_branch = 'Software\\BaseALT\\Policies\\Packages'

    def __init__(self, storage):
        self.storage = storage
 
        install_branch = '{}\\{}%'.format(self.__hklm_branch, self.__install_key_name)
        remove_branch = '{}\\{}%'.format(self.__hklm_branch, self.__remove_key_name)
        sync_branch = '{}\\{}%'.format(self.__hklm_branch, self.__sync_key_name)
        self.fulcmd = list()
        self.fulcmd.append('/usr/libexec/gpupdate/pkcon_runner')
        self.fulcmd.append('--loglevel')
        logger = logging.getLogger()
        self.fulcmd.append(str(logger.level))
        self.install_packages_setting = self.storage.filter_hklm_entries(install_branch)
        self.remove_packages_setting = self.storage.filter_hklm_entries(remove_branch)
        self.sync_packages_setting = self.storage.filter_hklm_entries(sync_branch)
        self.flagSync = False

        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )
    def run(self):
        for flag in self.sync_packages_setting:
            if flag.data:
                self.flagSync = bool(int(flag.data))

        if 0 < self.install_packages_setting.count() or 0 < self.remove_packages_setting.count():
            if not self.flagSync:
                try:
                    subprocess.check_call(self.fulcmd)
                except Exception as exc:
                    logdata = dict()
                    logdata['msg'] = str(exc)
                    log('E55', logdata)
            else:
                try:
                    subprocess.Popen(self.fulcmd,close_fds=False)
                except Exception as exc:
                    logdata = dict()
                    logdata['msg'] = str(exc)
                    log('E55', logdata)

    def apply(self):
        if self.__module_enabled:
            log('D138')
            self.run()
        else:
            log('D139')


class package_applier_user(applier_frontend):
    __module_name = 'PackagesApplierUser'
    __module_experimental = True
    __module_enabled = False
    __install_key_name = 'Install'
    __remove_key_name = 'Remove'
    __sync_key_name = 'Sync'
    __hkcu_branch = 'Software\\BaseALT\\Policies\\Packages'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.fulcmd = list()
        self.fulcmd.append('/usr/libexec/gpupdate/pkcon_runner')
        self.fulcmd.append('--sid')
        self.fulcmd.append(self.sid)
        self.fulcmd.append('--loglevel')
        logger = logging.getLogger()
        self.fulcmd.append(str(logger.level))

        install_branch = '{}\\{}%'.format(self.__hkcu_branch, self.__install_key_name)
        remove_branch = '{}\\{}%'.format(self.__hkcu_branch, self.__remove_key_name)
        sync_branch = '{}\\{}%'.format(self.__hkcu_branch, self.__sync_key_name)

        self.install_packages_setting = self.storage.filter_hkcu_entries(self.sid, install_branch)
        self.remove_packages_setting = self.storage.filter_hkcu_entries(self.sid, remove_branch)
        self.sync_packages_setting = self.storage.filter_hkcu_entries(self.sid, sync_branch)
        self.flagSync = True

        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_enabled)

    def user_context_apply(self):
        '''
        There is no point to implement this behavior.
        '''
        pass

    def run(self):
        for flag in self.sync_packages_setting:
            if flag.data:
                self.flagSync = bool(int(flag.data))

        if 0 < self.install_packages_setting.count() or 0 < self.remove_packages_setting.count():
            if self.flagSync:
                try:
                    subprocess.check_call(self.fulcmd)
                except Exception as exc:
                    logdata = dict()
                    logdata['msg'] = str(exc)
                    log('E55', logdata)
            else:
                try:
                    subprocess.Popen(self.fulcmd,close_fds=False)
                except Exception as exc:
                    logdata = dict()
                    logdata['msg'] = str(exc)
                    log('E55', logdata)

    def admin_context_apply(self):
        '''
        Install software assigned to specified username regardless
        which computer he uses to log into system.
        '''
        if self.__module_enabled:
            log('D140')
            self.run()
        else:
            log('D141')

