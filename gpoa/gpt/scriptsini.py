#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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

from .dynamic_attributes import DynamicAttributes


def read_scripts(scripts_file):
    scripts = Scripts_lists()

    logon_scripts = {}
    logoff_scripts = {}
    startup_scripts = {}
    shutdown_scripts = {}

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
                    section_scripts[key_index] = Script(act, scripts_file_dir, config[act][key])
            key_split = key_lower.split('parameters')
            if len(key_split) > 1 and not key_split[1]:
                if key_split[0].isdigit():
                    key_index = int(key_split[0])
                    section_scripts[key_index].set_args(config[act][key])
    if logon_scripts:
        for i in sorted(logon_scripts.keys()):
            scripts.add_script('LOGON', logon_scripts[i])

    if logoff_scripts:
        for i in sorted(logoff_scripts.keys()):
            scripts.add_script('LOGOFF', logoff_scripts[i])

    if startup_scripts:
        for i in sorted(startup_scripts.keys()):
            scripts.add_script('STARTUP', startup_scripts[i])

    if shutdown_scripts:
        for i in sorted(shutdown_scripts.keys()):
            scripts.add_script('SHUTDOWN', shutdown_scripts[i])


    return scripts

def merge_scripts(storage, scripts_objects, policy_name):
    for script in scripts_objects.get_logon_scripts():
        storage.add_script(script, policy_name)
    for script in scripts_objects.get_logoff_scripts():
        storage.add_script(script, policy_name)
    for script in scripts_objects.get_startup_scripts():
        storage.add_script(script, policy_name)
    for script in scripts_objects.get_shutdown_scripts():
        storage.add_script(script, policy_name)

class Scripts_lists:
    def __init__ (self):
        self.__logon_scripts = []
        self.__logoff_scripts = []
        self.__startup_scripts = []
        self.__shutdown_scripts = []

    def get_logon_scripts(self):
        return self.__logon_scripts
    def get_logoff_scripts(self):
        return self.__logoff_scripts
    def get_startup_scripts(self):
        return self.__startup_scripts
    def get_shutdown_scripts(self):
        return self.__shutdown_scripts

    def add_script(self, action, script):
        if action == 'LOGON':
            self.get_logon_scripts().append(script)
        elif action == 'LOGOFF':
            self.get_logoff_scripts().append(script)
        elif action == 'STARTUP':
            self.get_startup_scripts().append(script)
        elif action == 'SHUTDOWN':
            self.get_shutdown_scripts().append(script)


class Script(DynamicAttributes):
    __logon_counter = 0
    __logoff_counter = 0
    __startup_counter = 0
    __shutdown_counter = 0

    def __init__(self, action, script_dir, script_filename):
        action_upper = action.upper()
        self.action = action_upper
        self.path = os.path.join(script_dir, action_upper, script_filename.upper())
        if not os.path.isfile(self.path):
            self.number = None
            return None
        self.args = None

        if action_upper == 'LOGON':
            self.number = Script.__logon_counter
            Script.__logon_counter += 1
        elif action_upper == 'LOGOFF':
            self.number = Script.__logoff_counter
            Script.__logoff_counter += 1
        elif action_upper == 'STARTUP':
            self.number = Script.__startup_counter
            Script.__startup_counter += 1
        elif action_upper == 'SHUTDOWN':
            self.number = Script.__shutdown_counter
            Script.__shutdown_counter += 1

    def set_args(self, args):
        self.args = args

