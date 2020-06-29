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
    __hklm_branch = 'Software\\BaseALT\\Policies\\Packages'

    def __init__(self, storage):
        self.storage = storage
 
        install_branch = '{}\\{}%'.format(self.__hklm_branch, self.__install_key_name)
        remove_branch = '{}\\{}%'.format(self.__hklm_branch, self.__remove_key_name)

        self.install_packages_setting = self.storage.filter_hklm_entries(install_branch)
        self.remove_packages_setting = self.storage.filter_hklm_entries(remove_branch)

        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        if 0 < len(self.install_packages_setting) or 0 < len(self.remove_packages_setting):
            update()
            for package in self.install_packages_setting:
                try:
                    install_rpm(package.data)
                except Exception as exc:
                    logging.error(exc)

            for package in self.remove_packages_setting:
                try:
                    remove_rpm(package.data)
                except Exception as exc:
                    logging.error(exc)

    def apply(self):
        if self.__module_enabled:
            self.run()


class package_applier_user(applier_frontend):
    __module_name = 'PackagesApplierUser'
    __module_experimental = True
    __module_enabled = False
    __install_key_name = 'Install'
    __remove_key_name = 'Remove'
    __hkcu_branch = 'Software\\BaseALT\\Policies\\Packages'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

        install_branch = '{}\\{}%'.format(self.__hkcu_branch, self.__install_key_name)
        remove_branch = '{}\\{}%'.format(self.__hkcu_branch, self.__remove_key_name)

        self.install_packages_setting = self.storage.filter_hkcu_entries(self.sid, install_branch)
        self.remove_packages_setting = self.storage.filter_hkcu_entries(self.sid, remove_branch)

        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_enabled)

    def user_context_apply(self):
        '''
        There is no point to implement this behavior.
        '''
        pass

    def run(self):
        if 0 < len(self.install_packages_setting) or 0 < len(self.remove_packages_setting):
            update()
            for package in self.install_packages_setting:
                try:
                    install_rpm(package.data)
                except Exception as exc:
                    logging.debug(exc)

            for package in self.remove_packages_setting:
                try:
                    remove_rpm(package.data)
                except Exception as exc:
                    logging.debug(exc)

    def admin_context_apply(self):
        '''
        Install software assigned to specified username regardless
        which computer he uses to log into system.
        '''
        if self.__module_enabled:
            self.run()

