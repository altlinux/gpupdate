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

from .applier_frontend import applier_frontend
from .appliers.rpm import rpm

class package_applier(applier_frontend):
    def __init__(self, storage):
        self.storage = storage
        self.package_applier_settings = self.storage.filter_hklm_entries('Software\\BaseALT\\Policies\\Packages%')

    def apply(self):
        packages_for_install = ''
        packages_for_remove = ''

        for setting in self.package_applier_settings:
            action = setting.hive_key.rpartition('\\')[2]
            if action == 'PackagesForInstall':
                packages_for_install = setting.data
            if action == 'PackagesForRemove':
                packages_for_remove = setting.data

        if packages_for_install or packages_for_remove:
            r = rpm(packages_for_install, packages_for_remove)
            r.apply()


class package_applier_user(applier_frontend):
    def __init__(self):
        pass

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
        pass

