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

import configparser
import re


def read_scripts(scripts_file):
    scripts = set()
    config = configparser.ConfigParser()
    config.read(scripts_file, encoding = 'utf-16')
    actions = config.sections()
    for act in actions:
        count_qu = list()
        for key in config[act]:
            qu = re.sub(r'[a-zA-Z]', '', key)
            if qu not in count_qu:
                obj_scr = script(act)
                obj_scr.queue = qu
                count_qu.append(qu)

            if key.lower().find('cmdline') != -1 and count_qu:
                obj_scr.path = '{}{}/{}'.format(
                    scripts_file.removesuffix(scripts_file.split('/')[-1]),
                    act.upper(),
                    config[act][key].upper())
            if key.lower().find('parameters') != -1 and count_qu:
                obj_scr.arg = config[act][key]
            scripts.add(obj_scr)

    return list(scripts)

def merge_scripts(storage, sid, scripts_objects, policy_name, policy_num):
    for script in scripts_objects:
        script.policy_num = policy_num
        storage.add_script(sid, script, policy_name)


class script:
    def __init__(self, action):
        self.action = action
        self.queue = str()
        self.policy_num = str()
        self.path = str()
        self.arg = str()

    def set_obj(self, qu):
        if qu is not self.queue:
            self.queue = qu

    def add_item(self,qu, data):
        self.qu[qu].append(data)

    def checke_qu(self, qu):
        if qu in self.qu.keys():
            return True
        else:
            return False
