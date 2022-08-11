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
from .folder import str2bool
from util.logging import log
import shutil
from pathlib import Path
import configparser

class Ini_file:
    def __init__(self, arg_dict):
        self.path = arg_dict['path']
        self.section = arg_dict['section']
        self.action = action_letter2enum(arg_dict['action'])
        self.key = arg_dict['property']
        self.value = arg_dict['value']

        self.config = configparser.ConfigParser()

    def _create_action(self):
        if self.section not in self.config:
            self.config[self.section] = dict()

        self.config[self.section][self.key] = self.value

        with self.path.open("w", encoding="utf-8") as configfile:
            self.config.write(configfile)



    def _delete_action(self):
        if not self.path.exists():
            return

        if not self.section:
            self.path.unlink()
            return
        if not self.key:
            self.config.remove_section(self.section)
        elif self.section in self.config:
            self.config.remove_option(self.section, self.key)

        with self.path.open("w", encoding="utf-8") as configfile:
            self.config.write(configfile)


    def _update_action(self):
        pass

    def act(self):
        try:
            self.config.read(self.path)
        except Exception as exc:
            print('D!!!')
            return
        if self.action == FileAction.CREATE:
            self._create_action()
        if self.action == FileAction.UPDATE:
            self._delete_action()
            self._create_action()
        if self.action == FileAction.DELETE:
            self._delete_action()
        if self.action == FileAction.REPLACE:
            self._delete_action()
            self._create_action()

