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
from util.logging import log

from .applier_frontend import (
      applier_frontend
    , check_enabled
)

class scripts_applier(applier_frontend):
    __module_name = 'ScriptsApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, sid):
        self.storage = storage
        self.sid = sid
        self.scripts = self.storage.get_scripts(self.sid)
        for ts in self.scripts:
            pass

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

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.scripts = self.storage.get_scripts(self.sid)
        for ts in self.scripts:
            pass


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

