#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from .appliers.envvar import Envvar
from util.logging import log


class envvar_applier(applier_frontend):
    __module_name = 'EnvvarsApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.envvars = self.storage.get_envvars(self.sid)
        Envvar.clear_envvar_file()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def apply(self):
        if self.__module_enabled:
            log('D134')
            ev = Envvar(self.envvars, 'root')
            ev.act()
        else:
            log('D135')

class envvar_applier_user(applier_frontend):
    __module_name = 'EnvvarsApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.envvars = self.storage.get_envvars(self.sid)
        Envvar.clear_envvar_file(username)
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)

    def admin_context_apply(self):
        if self.__module_enabled:
            log('D136')
            ev = Envvar(self.envvars, self.username)
            ev.act()
        else:
            log('D137')

    def user_context_apply(self):
        pass

