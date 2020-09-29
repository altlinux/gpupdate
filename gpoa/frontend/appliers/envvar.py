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

from os.path import isfile
from util.logging import slogm
import logging

from gpt.envvars import (
      FileAction
    , action_letter2enum
)
from util.windows import expand_windows_var
from util.util import (
        get_homedir,
        homedir_exists
)

class Envvar:
    def __init__(self, envvars, username=''):
        self.username = username
        self.envvars = envvars
        if self.username == 'root':
            self.envvar_file_path = '/etc/gpupdate/environment'
        else:
            self.envvar_file_path = get_homedir(self.username) + '/.gpupdate_environment'

    def _open_envvar_file(self):
        fd = None
        if isfile(self.envvar_file_path):
            fd = open(self.envvar_file_path, 'r+')
        else:
            fd = open(self.envvar_file_path, 'w')
            fd.close()
            fd = open(self.envvar_file_path, 'r+')
        return fd

    def _create_action(self, create_dict, envvar_file):
        lines_old = envvar_file.readlines()
        lines_new = list()
        for name in create_dict:
            exist = False
            for line in lines_old:
                if line.startswith(name + '='):
                    exist = True
                    break
            if not exist:
                lines_new.append(name + '=' + create_dict[name] + '\n')
        if len(lines_new) > 0:
            envvar_file.writelines(lines_new)

    def _delete_action(self, delete_dict, envvar_file):
        lines = envvar_file.readlines()
        deleted = False
        for name in delete_dict:
            for line in lines:
                if line.startswith(name + '='):
                    lines.remove(line)
                    deleted = True
                    break
        if deleted:
            envvar_file.writelines(lines)

    def act(self):
        envvar_file = self._open_envvar_file()
        ev_create = dict()
        ev_update = dict()
        ev_delete = dict()
        ev_replace = dict()
        for envvar_object in self.envvars:
            action = action_letter2enum(envvar_object.action)
            name = envvar_object.name
            value = expand_windows_var(envvar_object.value, self.username).replace('\\', '/')

            if action == FileAction.CREATE:
                ev_create[name]=value
            if action == FileAction.UPDATE:
                ev_update[name]=value
            if action == FileAction.DELETE:
                ev_delete[name]=value
            if action == FileAction.REPLACE:
                ev_replace[name]=value

        self._create_action(ev_create, envvar_file)
        #self._update_action(ev_update, envvar_file)
        self._delete_action(ev_delete, envvar_file)
        #self._replace_action(ev_replace, envvar_file)

        envvar_file.close()

