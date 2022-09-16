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



from gpt.folders import (
      FileAction
    , action_letter2enum
)
from util.logging import log
from util.windows import expand_windows_var



class Networkshare:
    def __init__(self, networkshare_obj):
        self.name = networkshare_obj.name
        self.path = expand_windows_var(networkshare_obj.path).replace('\\', '/')
        self.action = action_letter2enum(networkshare_obj)
        self.allRegular =  networkshare_obj.allRegular
        self.comment = networkshare_obj.comment
        self.limitUsers = networkshare_obj.limitUsers
        self.abe = networkshare_obj.abe
        self.act()

    def _create_action(self):
        pass

    def _delete_action(self):
        pass

    def act(self):
        if self.action == FileAction.CREATE:
            self._create_action()
        if self.action == FileAction.UPDATE:
            self._create_action()
        if self.action == FileAction.DELETE:
            self._delete_action()
        if self.action == FileAction.REPLACE:
            self._create_action()
