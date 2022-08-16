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
from pathlib import Path
import configparser
from util.windows import expand_windows_var
from util.util import get_homedir



class Ini_file:
    def __init__(self, ini_obj, username=None):
        path = expand_windows_var(ini_obj.path, username).replace('\\', '/')
        self.path = check_path(path, username)
        if not self.path:
            logdata = {'path': ini_obj.path}
            log('D175', logdata)
            return None
        self.section = ini_obj.section
        self.action = action_letter2enum(ini_obj.action)
        self.key = ini_obj.property
        self.value = ini_obj.value
        self.config = configparser.ConfigParser()
        self.act()

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


    def act(self):
        try:
            self.config.read(self.path)
        except Exception as exc:
            logdata = {'exc': exc}
            log('D176', logdata)
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

def check_path(path_to_check, username = None):
    '''
    Function for checking the right path for Inifile
    '''
    checking = Path(path_to_check)
    if checking.exists():
        if username and path_to_check == '/':
            return Path(get_homedir(username))
        return checking
    #Check for path directory without '/nameIni' suffix
    elif (len(path_to_check.split('/')) > 2
          and Path(path_to_check.replace(path_to_check.split('/')[-1], '')).is_dir()):
        return checking
    elif username:
        target_path = Path(get_homedir(username))
        res = target_path.joinpath(path_to_check
                                    if path_to_check[0] != '/'
                                    else path_to_check[1:])
        return check_path(res)
    else:
        return False
