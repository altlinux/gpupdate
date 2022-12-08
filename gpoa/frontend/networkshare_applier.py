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

from .appliers.netshare import Networkshare
from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import log

class networkshare_applier(applier_frontend):
    __module_name = 'NetworksharesApplier'
    __module_name_user = 'NetworksharesApplierUser'
    __module_experimental = True
    __module_enabled = False

    def __init__(self, storage, sid, username = None):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.networkshare_info = self.storage.get_networkshare(self.sid)
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.__module_enabled_user = check_enabled(self.storage, self.__module_name_user, self.__module_experimental)

    def run(self):
        for networkshare in self.networkshare_info:
            if self.username:
                Networkshare(networkshare, self.username)
            else:
                Networkshare(networkshare)

    def apply(self):
        if self.__module_enabled:
            log('D187')
            self.run()
        else:
            log('D181')
    def admin_context_apply(self):
        pass

    def user_context_apply(self):
        if self.__module_enabled_user:
            log('D188')
            self.run()
        else:
            log('D189')
