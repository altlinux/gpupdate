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
import os


def read_scripts(scripts_file):
    scripts = scripts_lists()

    logon_scripts = dict()
    logoff_scripts = dict()
    startup_scripts = dict()
    shutdown_scripts = dict()

    config = configparser.ConfigParser()
    config.read(scripts_file, encoding = 'utf-16')
    scripts_file_dir = os.path.dirname(scripts_file)

    actions = config.sections()
    for act in actions:
        act_upper = act.upper()
        if act_upper == 'LOGON':
            section_scripts = logon_scripts
        elif act_upper == 'LOGOFF':
            section_scripts = logoff_scripts
        elif act_upper == 'STARTUP':
            section_scripts = startup_scripts
        elif act_upper == 'SHUTDOWN':
            section_scripts = shutdown_scripts
        else:
            continue

        for key in config[act]:
            key_lower = key.lower()
            key_split = key_lower.split('cmdline')
            if len(key_split) > 1 and not key_split[1]:
                if key_split[0].isdigit():
                    key_index = int(key_split[0])
                    section_scripts[key_index] = script(act, scripts_file_dir, config[act][key])
            key_split = key_lower.split('parameters')
            if len(key_split) > 1 and not key_split[1]:
                if key_split[0].isdigit():
                    key_index = int(key_split[0])
                    script = section_scripts.get(key_index)
                    if script: script.set_args(config[act][key])

        for i in sorted(logon_scripts.keys()):
            scripts_lists.add_script(logon_scripts[i])
        for i in sorted(logoff_scripts.keys()):
            scripts_lists.add_script(logoff_scripts[i])
        for i in sorted(startup_scripts.keys()):
            scripts_lists.add_script(startup_scripts[i])
        for i in sorted(shutdown_scripts.keys()):
            scripts_lists.add_script(shutdown_scripts[i])


    return scripts

def merge_scripts(storage, sid, scripts_objects, policy_name):
    for script in scripts_objects.get_logon_scripts():
        storage.add_logon_script(sid, script)
    for script in scripts_objects.get_logoff_scripts():
        storage.add_logoff_script(sid, script)
    for script in scripts_objects.get_startup_scripts():
        storage.add_startup_script(sid, script)
    for script in scripts_objects.get_shutdown_scripts():
        storage.add_shutdown_script(sid, script)

class scripts_lists:
    def __init__ (self):
        self.__logon_scripts = list()
        self.__logoff_scripts = list()
        self.__startup_scripts = list()
        self.__shutdown_scripts = list()

    def get_logon_scripts(self, action):
        return self.__logon_scripts
    def get_logoff_scripts(self, action):
        return self.__logoff_scripts
    def get_startup_scripts(self, action):
        return self.__startup_scripts
    def get_shutdown_scripts(self, action):
        return self.__shutdown_scripts

    def add_script(self, action, script):
        self.get_action_list(action).append(script)
    def add_script(self, action, script):
        self.get_action_list(action).append(script)
    def add_script(self, action, script):
        self.get_action_list(action).append(script)
    def add_script(self, action, script):
        self.get_action_list(action).append(script)

class script:
    __logon_counter = 0
    __logoff_counter = 0
    __startup_counter = 0
    __shutdown_counter = 0

    def __init__(self, action, script_dir, script_filename):
        action_upper = action.upper()
        self.action = action_upper
        self.path = os.path.join(script_dir, action_upper, script_filename.upper())
        self.args = None

        if action_upper == 'LOGON':
            self.number = script.__logon_counter
            script.__logon_counter += 1
        elif action_upper == 'LOGOFF':
            self.number = script.__logoff_counter
            script.__logoff_counter += 1
        elif action_upper == 'STARTUP':
            self.number = script.__startup_counter
            script.__startup_counter += 1
        elif action_upper == 'SHUTDOWN':
            self.number = script.__shutdown_counter
            script.__shutdown_counter += 1

    def set_args(self, args):
        self.args = args

