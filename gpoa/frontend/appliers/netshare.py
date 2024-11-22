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

import subprocess

from util.arguments import (
      FileAction
    , action_letter2enum
)
from util.logging import log
from util.windows import expand_windows_var


class Networkshare:

    def __init__(self, networkshare_obj, username = None):
        self.net_full_cmd = ['/usr/bin/net', 'usershare']
        self.net_cmd_check = ['/usr/bin/net', 'usershare', 'list']
        self.cmd = list()
        self.name = networkshare_obj.name
        self.path = expand_windows_var(networkshare_obj.path, username).replace('\\', '/') if networkshare_obj.path else None

        self.action = action_letter2enum(networkshare_obj.action)
        self.allRegular =  networkshare_obj.allRegular
        self.comment = networkshare_obj.comment
        self.limitUsers = networkshare_obj.limitUsers
        self.abe = networkshare_obj.abe
        self._guest = 'guest_ok=y'
        self.acl = 'Everyone:'
        self.act()

    def check_list_net(self):
        try:
            res = subprocess.check_output(self.net_cmd_check, encoding='utf-8')
            return res
        except Exception as exc:
            return exc

    def _run_net_full_cmd(self):
        logdata = dict()
        try:
            res = subprocess.check_output(self.net_full_cmd, stderr=subprocess.DEVNULL, encoding='utf-8')
            if res:
                logdata['cmd'] = self.net_full_cmd
                logdata['answer'] = res
            log('D190', logdata)
        except Exception as exc:
            logdata['cmd'] = self.net_full_cmd
            logdata['exc'] = exc
            log('D182', logdata)


    def _create_action(self):
        self.net_full_cmd.append('add')
        self.net_full_cmd.append(self.name)
        self.net_full_cmd.append(self.path)
        self.net_full_cmd.append(self.comment)
        self.net_full_cmd.append(self.acl + 'F')
        self.net_full_cmd.append(self._guest)
        self._run_net_full_cmd()

    def _delete_action(self):
        self.net_full_cmd.append('delete')
        self.net_full_cmd.append(self.name)
        self._run_net_full_cmd()

    def act(self):
        if self.action == FileAction.CREATE:
            self._create_action()
        if self.action == FileAction.UPDATE:
            self._create_action()
        if self.action == FileAction.DELETE:
            self._delete_action()
        if self.action == FileAction.REPLACE:
            self._create_action()
