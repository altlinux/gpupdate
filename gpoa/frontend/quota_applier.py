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
from enum import Enum


from util.logging import slogm


class QuotaUnits(Enum):
    KILOBYTES = 1
    MEGABYTES = 2


class quota_applier:
    __registry_branch = 'Software\\Policies\\Microsoft\\Windows NT\\DiskQuota'
    __diskquota_key_enabled = 'Enable'
    # Hard limit
    __diskquota_key_limit = 'Limit'
    __diskquota_key_limit_units = 'LimitUnits'
    # Warning limit
    __diskquota_key_threshold = 'Threshold'
    __diskquota_key_threshold_units = 'ThresholdUnits'
    # Switch between hard and soft quota
    __diskquota_key_limit_type = 'Enforce'
    __module_name = 'QuotaApplier'
    __module_enabled = False
    __module_experimental = True

    def __init__(self, storage, username, sid):
        self.storage = storage
        self.username = username
        self.sid = sid

    def run(self):
        pass

    def apply(self):
        if self.__module_enabled:
            logging.debug(slogm('Running Quota applier for machine'))
            self.run()
        else:
            logging.debug(slogm('Quota applier for machine will not be started'))

