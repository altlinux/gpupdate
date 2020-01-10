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

from .applier_frontend import applier_frontend
from .appliers.systemd import systemd_unit
from util.logging import slogm

import logging

class systemd_applier(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\SystemdUnits'

    def __init__(self, storage):
        self.storage = storage
        self.systemd_unit_settings = self.storage.filter_hklm_entries('Software\\BaseALT\\Policies\\SystemdUnits%')
        self.units = []

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for setting in self.systemd_unit_settings:
            valuename = setting.hive_key.rpartition('\\')[2]
            try:
                self.units.append(systemd_unit(valuename, int(setting.data)))
                logging.info(slogm('Working with systemd unit {}'.format(valuename)))
            except Exception as exc:
                logging.info(slogm('Unable to work with systemd unit {}: {}'.format(valuename, exc)))
        for unit in self.units:
            try:
                unit.apply()
            except:
                logging.error(slogm('Failed applying unit {}'.format(unit.unit_name)))

class systemd_applier_user(applier_frontend):
    __registry_branch = 'Software\\BaseALT\\Policies\\SystemdUnits'

    def __init__(self, storage, sid, username):
        self.storage = storage

    def user_context_apply(self):
        pass

    def admin_context_apply(self):
        pass

