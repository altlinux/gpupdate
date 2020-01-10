#
# Copyright (C) 2019-2020 Igor Chudov
# Copyright (C) 2019-2020 Evgeny Sinelnikov
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

from .applier_frontend import applier_frontend
from .appliers.gsettings import (
    system_gsetting,
    user_gsetting
)

class gsettings_applier(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\gsettings'

    def __init__(self, storage):
        self.storage = storage
        gsettings_filter = '{}%'.format(self.__registry_branch)
        self.gsettings_keys = self.storage.filter_hklm_entries(gsettings_filter)
        self.gsettings = list()

    def apply(self):
        for setting in self.gsettings_keys:
            valuename = setting.hive_key.rpartition('\\')[2]
            rp = valuename.rpartition('.')
            schema = rp[0]
            path = rp[2]
            self.gsettings.append(system_gsetting(schema, path, setting.data))

        for gsetting in self.gsettings:
            gsetting.apply()

class gsettings_applier_user(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\gsettings'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        gsettings_filter = '{}%'.format(self.__registry_branch)
        self.gsettings_keys = self.storage.filter_hkcu_entries(self.sid, gsettings_filter)
        self.gsettings = list()

    def user_context_apply(self):
        for setting in self.gsettings_keys:
            valuename = setting.hive_key.rpartition('\\')[2]
            rp = valuename.rpartition('.')
            schema = rp[0]
            path = rp[2]
            self.gsettings.append(user_gsetting(schema, path, setting.data))

        for gsetting in self.gsettings:
            gsetting.apply()

    def admin_context_apply(self):
        pass

