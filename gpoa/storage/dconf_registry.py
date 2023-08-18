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


class PregDconf():
    def __init__(self, keyname, valuename, type_preg, data):
        self.keyname = keyname
        self.valuename = valuename
        self.hive_key = '{}\\{}'.format(self.keyname, self.valuename)
        self.type = type_preg
        self.data = data


class gplist(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def first(self):
        if self:
            return self[0]
        else:
            return None

    def count(self):
        return len(self)

class Dconf_registry():
    '''
    A class variable that represents a global registry dictionary shared among instances of the class
    '''
    _ReadQueue = 'Software/BaseALT/Policies/ReadQueue'
    global_registry_dict = dict({_ReadQueue:{}})
    global_registry_dict_win_style = dict()
    __template_file = '/usr/share/dconf/user_mandatory.template'

    list_keys = list()
    _info = dict()

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


    def filter_entries(self, startswith):
        if startswith[-1] == '%':
            startswith = startswith[:-1]
            return filter_dict_keys(startswith, Dconf_registry.global_registry_dict_win_style)
        return filter_dict_keys(startswith, Dconf_registry.global_registry_dict)


    def filter_hklm_entries(self, startswith):
        pregs = self.filter_entries(startswith)
        list_entiers = list()
        for keyname, value in pregs.items():
            for valuename, data in value.items():
                list_entiers.append(PregDconf(keyname, valuename, find_preg_type(data), data))
        return gplist(list_entiers)


    def filter_hkcu_entries(self, sid, startswith):
        return self.filter_hklm_entries(startswith)


    def get_entry(self, dictionary, path):
        keys = path.split("\\") if "\\" in path else path.split("/")
        result = dictionary
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return None
        return result

    def get_hkcu_entry(self, sid, hive_key):
        return self.get_hklm_entry(hive_key)


    def get_hklm_entry(self, hive_key):
        return self.get_entry(Dconf_registry.global_registry_dict_win_style, hive_key)


    def set_info(self, key , data):
        self._info[key] = data


    def get_info(self, key):
        return self._info.setdefault(key, None)


    def add_shortcut(self, sid, sc_obj, policy_name):
        self.shortcuts.append(sc_obj)


    def add_printer(self, sid, pobj, policy_name):
        self.printers.append(pobj)


    def add_drive(self, sid, dobj, policy_name):
        self.drives.append(dobj)


    def add_folder(self, sid, fobj, policy_name):
        self.folders.append(fobj)


    def add_envvar(self, sid, evobj, policy_name):
        self.environmentvariables.append(evobj)


    def add_script(self, sid, scrobj, policy_name):
        self.scripts.append(scrobj)


    def add_file(self, sid, fileobj, policy_name):
        self.files.append(fileobj)


    def add_ini(self, sid, iniobj, policy_name):
        self.inifiles.append(iniobj)


    def add_networkshare(self, sid, networkshareobj, policy_name):
        self.networkshares.append(networkshareobj)


    def get_shortcuts(self, sid):
        return self.shortcuts


    def get_printers(self, sid):
        return self.printers


    def get_drives(self, sid):
        return self.drives


    def get_folders(self, sid):
        return self.folders


    def get_envvars(self, sid):
        return self.environmentvariables


    def get_scripts(self, sid, action):
        action_scripts = list()
        for part in self.scripts:
            if action == 'LOGON':
                action_scripts.extend(part.get_logon_scripts())
            elif action == 'LOGOFF':
                action_scripts.extend(part.get_logoff_scripts())
            elif action == 'STARTUP':
                action_scripts.extend(part.get_startup_scripts())
            elif action == 'SHUTDOWN':
                action_scripts.extend(part.get_shutdown_scripts())
        return action_scripts



    def get_files(self, sid):
        return self.files


    def get_networkshare(self, sid):
        return self.networkshares


    def get_ini(self, sid):
        return self.inifiles


    def wipe_user(self, sid):
        ...

    def wipe_hklm(self):
        ...


def filter_dict_keys(starting_string, input_dict):
    return {key: input_dict[key] for key in input_dict if key.startswith(starting_string)}


def has_single_key_with_value(input_dict):

    if not input_dict or len(input_dict) == 0:
        return False
    elif len(input_dict) == 1 and list(input_dict.values())[0] is None:
        return False
    else:
        return True


def find_preg_type(argument):
    if isinstance(argument, int):
        return 4
    else:
        return 1


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
    dd_win_style = dict()
    for i in pregfile.entries:
        # Skip this entry if the valuename starts with '**del'
        if i.valuename.startswith('**del'):
            continue

        if i.valuename != i.data:
            if i.keyname.replace('\\', '/') in dd:
                # If the key exists in dd, update its value with the new key-value pair
                dd[i.keyname.replace('\\', '/')].update({i.valuename.replace('\\', '/'):i.data})
                dd_win_style[i.keyname].update({i.valuename:i.data})
            else:
                # If the key does not exist in dd, create a new key-value pair
                dd[i.keyname.replace('\\', '/')] = {i.valuename.replace('\\', '/'):i.data}
                dd_win_style[i.keyname] = {i.valuename:i.data}
        else:
            # If the value name is the same as the data,
            # split the keyname and add the data to the appropriate location in dd.
            all_list_key = i.keyname.split('\\')
            dd_target = dd.setdefault('/'.join(all_list_key[:-1]),{})
            dd_target.setdefault(all_list_key[-1], []).append(i.data)

            dd_target_win = dd_win_style.setdefault('\\'.join(all_list_key[:-1]),{})
            dd_target_win.setdefault(all_list_key[-1], []).append(i.data)
    # Update the global registry dictionary with the contents of dd
    add_to_dict(Dconf_registry.global_registry_dict[Dconf_registry._ReadQueue], pathfile)
    update_dict(Dconf_registry.global_registry_dict, dd)
    update_dict(Dconf_registry.global_registry_dict_win_style, dd_win_style)


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
