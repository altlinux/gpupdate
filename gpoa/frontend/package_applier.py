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
from util.logging import slogm
from util.rpm import (
      update
    , install_rpm
    , remove_rpm
)

from .applier_frontend import applier_frontend

class package_applier(applier_frontend):
    __install_key_name = 'PackagesForInstall'
    __remove_key_name = 'PackagesForRemove'
    __hklm_branch = 'Software\\BaseALT\\Policies\\Packages'

    def __init__(self, storage):
        self.storage = storage
 
        install_branch = '{}\\{}'.format(self.__hklm_branch, self.__install_key_name)
        remove_branch = '{}\\{}'.format(self.__hklm_branch, self.__remove_key_name)

        self.install_packages_setting = self.storage.get_hklm_entry(install_branch)
        self.install_packages = None
        if self.install_packages_setting:
            self.install_packages = self.install_packages_setting.data.split()

        self.remove_packages_setting = self.storage.get_hklm_entry(remove_branch)
        self.remove_packages = None
        if self.remove_packages_setting:
            self.remove_packages = self.remove_packages_setting.data.split()

    def apply(self):
        update()
        if self.install_packages:
            for package in self.install_packages:
                try:
                    install_rpm(package)
                except Exception as exc:
                    logging.error(exc)

        if self.remove_packages:
            for package in self.remove_packages:
                try:
                    remove_rpm(package)
                except Exception as exc:
                    logging.error(exc)


class package_applier_user(applier_frontend):
    __install_key_name = 'PackagesForInstall'
    __remove_key_name = 'PackagesForRemove'
    __hkcu_branch = 'Software\\BaseALT\\Policies\\Packages'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

        install_branch = '{}\\{}'.format(self.__hkcu_branch, self.__install_key_name)
        remove_branch = '{}\\{}'.format(self.__hkcu_branch, self.__remove_key_name)

        self.install_packages_setting = self.storage.get_hkcu_entry(self.sid, install_branch)
        self.install_packages = None
        if self.install_packages_setting:
            self.install_packages = self.install_packages_setting.data.split()

        self.remove_packages_setting = self.storage.get_hkcu_entry(self.sid, remove_branch)
        self.remove_packages = None
        if self.remove_packages_setting:
            self.remove_packages = self.remove_packages_setting.data.split()

    def user_context_apply(self):
        '''
        There is no point to implement this behavior.
        '''
        pass

    def admin_context_apply(self):
        '''
        Install software assigned to specified username regardless
        which computer he uses to log into system.
        '''
        update()
        if self.install_packages:
            for package in self.install_packages:
                try:
                    install_rpm(package)
                except Exception as exc:
                    logging.debug(exc)

        if self.remove_packages:
            for package in self.remove_packages:
                try:
                    remove_rpm(package)
                except Exception as exc:
                    logging.debug(exc)

