#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2023 BaseALT Ltd.
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
from pathlib import Path
from util.util import string_to_literal_eval, get_uid_by_username, touch_file
from util.paths import get_dconf_config_path

class Dconf_registry():
    '''
    A class variable that represents a global registry dictionary shared among instances of the class
    '''
    _ReadQueue = 'Software/BaseALT/Policies/ReadQueue'
    global_registry_dict = dict({_ReadQueue:{}})
    __template_file = '/usr/share/dconf/user_mandatory.template'

    list_keys = list()

    shortcuts = list()
    folders = list()
    files = list()
    drives = list()
    scheduledtasks = list()
    environmentvariables = list()
    inifiles = list()
    services = list()
    printers = list()
    scripts = list()
    networkshares = list()

    def __init__(self, username, is_machine):
        self.username = username
        self.is_machine = is_machine
        self.uid = get_uid_by_username(username) if not is_machine else None
        target_file = get_dconf_config_path(self.uid)
        touch_file(target_file)
        self.apply_template()
        create_dconf_ini_file(target_file,Dconf_registry.global_registry_dict)

    @staticmethod
    def get_matching_keys(path):
        try:
            process = subprocess.Popen(['dconf', 'list', path],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()
            if not output and not error:
                return
            if not error:
                keys = output.strip().split('\n')
                for key in keys:
                    Dconf_registry.get_matching_keys(f'{path}{key}')
            else:
                Dconf_registry.list_keys.append(path)
            return Dconf_registry.list_keys
        except Exception as exc:
            #log
            return None

    @staticmethod
    def get_key_values(keys):
        key_values = {}
        try:
            for key in keys:
                process = subprocess.Popen(['dconf', 'read', key],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                output, error = process.communicate()

                if not error:
                    key_values[key] = string_to_literal_eval(string_to_literal_eval(output))
        except Exception as exc:
            #log
            ...
        return key_values

    @staticmethod
    def dconf_update():
        try:
            process = subprocess.Popen(['dconf', 'update'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()

            if error:
                #log error
                ...
            else:
                #log done
                ...
        except Exception as exc:
            #log exp
            ...

    def check_profile_template(self):
        if Path(self.__template_file).exists():
            return True
        else:
            return None

    def apply_template(self):
        if self.uid and self.check_profile_template():
            with open(self.__template_file, "r") as f:
                template = f.read()
            # Replace the "{uid}" placeholder with the actual UID value
            content = template.replace("{{uid}}", str(self.uid))

        elif self.uid:
            content = f"user-db:user\n" \
              f"system-db:policy\n" \
              f"system-db:policy{self.uid}\n" \
              f"system-db:local\n" \
              f"system-db:default\n" \
              f"system-db:local\n" \
              f"system-db:policy{self.uid}\n" \
              f"system-db:policy\n"
        else:
            return

        user_mandatory = f'/run/dconf/user/{self.uid}'
        touch_file(user_mandatory)

        with open(user_mandatory, "w") as f:
            f.write(content)

def filter_dict_keys(starting_string, input_dict):
    return {key: input_dict[key] for key in input_dict if key.startswith(starting_string)}

def has_single_key_with_value(input_dict):

    if not input_dict or len(input_dict) == 0:
        return False
    elif len(input_dict) == 1 and list(input_dict.values())[0] is None:
        return False
    else:
        return True

def update_dict(dict1, dict2):
    '''
    Updates dict1 with the key-value pairs from dict2
    '''
    for key, value in dict2.items():
        if key in dict1:
            # If both values are dictionaries, recursively call the update_dict function
            if isinstance(dict1[key], dict) and isinstance(value, dict):
                update_dict(dict1[key], value)
            else:
                # If the value in dict1 is not a dictionary or the value in dict2 is not a dictionary,
                # replace the value in dict1 with the value from dict2
                dict1[key] = value
        else:
            # If the key does not exist in dict1, add the key-value pair from dict2 to dict1
            dict1[key] = value


def add_to_dict(dictionary, string):
    correct_path = '/'.join(string.split('/')[:-2])
    dictionary[len(dictionary)] = correct_path


def load_preg_dconf(pregfile, pathfile):
    '''
    Loads the configuration from preg registry into a dictionary
    '''
    dd = dict()
    for i in pregfile.entries:
        # Skip this entry if the valuename starts with '**del'
        if i.valuename.startswith('**del'):
            continue

        if i.valuename != i.data:
            if i.keyname.replace('\\', '/') in dd:
                # If the key exists in dd, update its value with the new key-value pair
                dd[i.keyname.replace('\\', '/')].update({i.valuename.replace('\\', '/'):i.data})
            else:
                # If the key does not exist in dd, create a new key-value pair
                dd[i.keyname.replace('\\', '/')] = {i.valuename.replace('\\', '/'):i.data}
        else:
            # If the value name is the same as the data,
            # split the keyname and add the data to the appropriate location in dd.
            all_list_key = i.keyname.split('\\')
            dd_target = dd.setdefault('/'.join(all_list_key[:-1]),{})
            dd_target.setdefault(all_list_key[-1], []).append(i.data)
    # Update the global registry dictionary with the contents of dd
    add_to_dict(Dconf_registry.global_registry_dict[Dconf_registry._ReadQueue], pathfile)
    update_dict(Dconf_registry.global_registry_dict, dd)


def create_dconf_ini_file(filename, data):
    '''
    Create an ini-file based on a dictionary of dictionaries.
    Args:
        data (dict): The dictionary of dictionaries containing the data for the ini-file.
        filename (str): The filename to save the ini-file.
    Returns:
        None
    Raises:
        None
    '''
    with open(filename, 'w') as file:
        for section, section_data in data.items():
            file.write(f'[{section}]\n')
            for key, value in section_data.items():
                if isinstance(value, int):
                    file.write(f'{key} = {value}\n')
                else:
                    file.write(f'{key} = "{value}"\n')
            file.write('\n')
