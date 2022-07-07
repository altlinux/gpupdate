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

from pathlib import Path

from gpt.folders import (
      FileAction
    , action_letter2enum
)
from .folder import str2bool


class Files_cp:
    def __init__(self, arg_dict):
        self.fromPath = Path(arg_dict['fromPath'])
        self.targetPath = Path(arg_dict['targetPath'])
        self.action = action_letter2enum(arg_dict['action'])
        self.readOnly = str2bool(arg_dict['readOnly'])
        self.archive = str2bool(arg_dict['archive'])
        self.hidden = str2bool(arg_dict['hidden'])
        self.suppress = str2bool(arg_dict['suppress'])

    def _create_action(self):
        pass

    def _delete_action(self):
        pass

    def _update_action(self):
        pass

    def act(self):
        if self.action == FileAction.CREATE:
            self._create_action()
        if self.action == FileAction.UPDATE:
            self._create_action()
        if self.action == FileAction.DELETE:
            self._delete_action()
        if self.action == FileAction.REPLACE:
            self._delete_action()
            self._create_action()

