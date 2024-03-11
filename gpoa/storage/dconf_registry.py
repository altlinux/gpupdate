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
from util.util import string_to_literal_eval, touch_file, get_uid_by_username
from util.logging import log
import re


class PregDconf():
    def __init__(self, keyname, valuename, type_preg, data):
        self.keyname = keyname
        self.valuename = valuename
        self.hive_key = '{}/{}'.format(self.keyname, self.valuename)
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
    __template_file = '/usr/share/dconf/user_mandatory.template'
    _policies_path = 'Software/'
    _policies_win_path = 'SOFTWARE/'
    _gpt_read_flag = False
    __dconf_dict_flag = False
    __dconf_dict = dict()
    _username = None
    _envprofile = None

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



    @classmethod
    def set_info(cls, key , data):
        cls._info[key] = data


    @classmethod
    def get_info(cls, key):
        return cls._info.setdefault(key, None)


    @staticmethod
    def get_matching_keys(path):
        if path[0] != '/':
            path = '/' + path
        logdata = dict()
        envprofile = get_dconf_envprofile()
        try:
            process = subprocess.Popen(['dconf', 'list', path],
                                       env=envprofile, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logdata['path'] = path
            log('D204', logdata)
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
            logdata['exc'] = exc
            log('E69', logdata)
            return None

    @staticmethod
    def get_key_values(keys):
        key_values = {}
        for key in keys:
            key_values[key] = Dconf_registry.get_key_value(key)
        return key_values

    @staticmethod
    def get_key_value(key):
        logdata = dict()
        envprofile = get_dconf_envprofile()
        try:
            process = subprocess.Popen(['dconf', 'read', key],
                                       env=envprofile, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logdata['key'] = key
            output, error = process.communicate()

            if not error:
                return string_to_literal_eval(string_to_literal_eval(output))
            else:
                return None
        except Exception as exc:
            logdata['exc'] = exc
            log('E70', logdata)
        return None

    @staticmethod
    def dconf_update():
        logdata = dict()
        try:
            process = subprocess.Popen(['dconf', 'update'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()

            if error:
                logdata['error'] = error
                log('E71', logdata)
            else:
                logdata['outpupt'] = output
                log('D206', logdata)
        except Exception as exc:
            logdata['exc'] = exc
            log('E72', logdata)

    @classmethod
    def check_profile_template(cls):
        if Path(cls.__template_file).exists():
            return True
        else:
            return None

    @classmethod
    def apply_template(cls, uid):
        logdata = dict()
        if uid and cls.check_profile_template():
            with open(cls.__template_file, "r") as f:
                template = f.read()
            # Replace the "{uid}" placeholder with the actual UID value
            content = template.replace("{{uid}}", str(uid))

        elif uid:
            content = f"user-db:user\n" \
              f"system-db:policy\n" \
              f"system-db:policy{uid}\n" \
              f"system-db:local\n" \
              f"system-db:default\n" \
              f"system-db:local\n" \
              f"system-db:policy{uid}\n" \
              f"system-db:policy\n"
        else:
            logdata['uid'] = uid
            log('W24', logdata)
            return

        user_mandatory = f'/run/dconf/user/{uid}'
        touch_file(user_mandatory)

        with open(user_mandatory, "w") as f:
            f.write(content)


    @classmethod
    def get_policies_from_dconf(cls):
        return cls.get_dictionary_from_dconf(cls._policies_path, cls._policies_win_path)


    @classmethod
    def get_dictionary_from_dconf(self, *startswith_list):
        output_dict = {}
        for startswith in startswith_list:
            dconf_dict = self.get_key_values(self.get_matching_keys(startswith))
            for key, value in dconf_dict.items():
                keys_tmp = key.split('/')
                update_dict(output_dict.setdefault('/'.join(keys_tmp[:-1])[1:], {}), {keys_tmp[-1]: value})

        log('D207')
        return output_dict


    @classmethod
    def filter_entries(cls, startswith):
        if startswith[-1] == '%':
            startswith = startswith[:-1]
            if startswith[-1] == '/' or startswith[-1] == '\\':
                startswith = startswith[:-1]
            return filter_dict_keys(startswith, flatten_dictionary(cls.global_registry_dict))
        return filter_dict_keys(startswith, flatten_dictionary(cls.global_registry_dict))


    @classmethod
    def filter_hklm_entries(cls, startswith):
        pregs = cls.filter_entries(startswith)
        list_entiers = list()
        for keyname, value in pregs.items():
            if isinstance(value, dict):
                for valuename, data in value.items():
                    list_entiers.append(PregDconf(
                        keyname, convert_string_dconf(valuename), find_preg_type(data), data))
            elif isinstance(value, list):
                for data in value:
                    list_entiers.append(PregDconf(
                        keyname, convert_string_dconf(data), find_preg_type(data), data))
            else:
                list_entiers.append(PregDconf(
                        '/'.join(keyname.split('/')[:-1]), convert_string_dconf(keyname.split('/')[-1]), find_preg_type(value), value))


        return gplist(list_entiers)


    @classmethod
    def filter_hkcu_entries(cls, sid, startswith):
        return cls.filter_hklm_entries(startswith)


    @classmethod
    def get_storage(cls,dictionary = None):
        if dictionary:
            result = dictionary
        elif Dconf_registry._gpt_read_flag:
            result = Dconf_registry.global_registry_dict
        else:
            if Dconf_registry.__dconf_dict_flag:
                result = Dconf_registry.__dconf_dict
            else:
                Dconf_registry.__dconf_dict = Dconf_registry.get_policies_from_dconf()
                result = Dconf_registry.__dconf_dict
                Dconf_registry.__dconf_dict_flag = True
        return result


    @classmethod
    def filling_storage_from_dconf(cls):
        Dconf_registry.global_registry_dict = Dconf_registry.get_storage()


    @classmethod
    def get_entry(cls, path, dictionary = None):
        logdata = dict()
        result = Dconf_registry.get_storage(dictionary)

        keys = path.split("\\") if "\\" in path else path.split("/")
        key = '/'.join(keys[:-1]) if keys[0] else '/'.join(keys[:-1])[1:]

        if isinstance(result, dict) and key in result.keys():
            data = result.get(key).get(keys[-1])
            return PregDconf(
                key, convert_string_dconf(keys[-1]), find_preg_type(data), data)
        else:
            logdata['path'] = path
            log('D208', logdata)
            return None


    @classmethod
    def get_hkcu_entry(cls, sid, hive_key, dictionary = None):
        return cls.get_hklm_entry(hive_key, dictionary)


    @classmethod
    def get_hklm_entry(cls, hive_key, dictionary = None):
        return cls.get_entry(hive_key, dictionary)



    @classmethod
    def add_shortcut(cls, sid, sc_obj, policy_name):
        cls.shortcuts.append(sc_obj)


    @classmethod
    def add_printer(cls, sid, pobj, policy_name):
        cls.printers.append(pobj)


    @classmethod
    def add_drive(cls, sid, dobj, policy_name):
        cls.drives.append(dobj)


    @classmethod
    def add_folder(cls, sid, fobj, policy_name):
        cls.folders.append(fobj)


    @classmethod
    def add_envvar(self, sid, evobj, policy_name):
        self.environmentvariables.append(evobj)


    @classmethod
    def add_script(cls, sid, scrobj, policy_name):
        cls.scripts.append(scrobj)


    @classmethod
    def add_file(cls, sid, fileobj, policy_name):
        cls.files.append(fileobj)


    @classmethod
    def add_ini(cls, sid, iniobj, policy_name):
        cls.inifiles.append(iniobj)


    @classmethod
    def add_networkshare(cls, sid, networkshareobj, policy_name):
        cls.networkshares.append(networkshareobj)


    @classmethod
    def get_shortcuts(cls, sid):
        return cls.shortcuts


    @classmethod
    def get_printers(cls, sid):
        return cls.printers


    @classmethod
    def get_drives(cls, sid):
        return cls.drives

    @classmethod
    def get_folders(cls, sid):
        return cls.folders


    @classmethod
    def get_envvars(cls, sid):
        return cls.environmentvariables


    @classmethod
    def get_scripts(cls, sid, action):
        action_scripts = list()
        for part in cls.scripts:
            if action == 'LOGON':
                action_scripts.append(part)
            elif action == 'LOGOFF':
                action_scripts.append(part)
            elif action == 'STARTUP':
                action_scripts.append(part)
            elif action == 'SHUTDOWN':
                action_scripts.append(part)
        return action_scripts


    @classmethod
    def get_files(cls, sid):
        return cls.files


    @classmethod
    def get_networkshare(cls, sid):
        return cls.networkshares


    @classmethod
    def get_ini(cls, sid):
        return cls.inifiles


    @classmethod
    def wipe_user(cls, sid):
        cls.wipe_hklm()


    @classmethod
    def wipe_hklm(cls):
        cls.global_registry_dict = dict({cls._ReadQueue:{}})


def filter_dict_keys(starting_string, input_dict):
    result = dict()
    for key in input_dict:
        key_list = remove_empty_values(re.split(r'\\|/', key))
        start_list = remove_empty_values(re.split(r'\\|/', starting_string))
        if key_list[:len(start_list)] == start_list:
            result[key] = input_dict.get(key)

    return result


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
            # If the value in dict1 is a list, extend it with unique values from value
            elif isinstance(dict1[key], list):
                dict1[key].extend(set(value) - set(dict1[key]))
            else:
                # If the value in dict1 is not a dictionary or the value in dict2 is not a dictionary,
                # replace the value in dict1 with the value from dict2
                dict1[key] = value
        else:
            # If the key does not exist in dict1, add the key-value pair from dict2 to dict1
            dict1[key] = value


def add_to_dict(string, policy_name, username):
    if username is None:
        correct_path = '/'.join(string.split('/')[:-2])
        machine= '{}/Machine'.format(Dconf_registry._ReadQueue)
        dictionary = Dconf_registry.global_registry_dict.setdefault(machine, dict())
    else:
        correct_path = '/'.join(string.split('/')[:-2])
        user = '{}/User'.format(Dconf_registry._ReadQueue)
        dictionary = Dconf_registry.global_registry_dict.setdefault(user, dict())

    dictionary[len(dictionary)] = (policy_name, correct_path)


def load_preg_dconf(pregfile, pathfile, policy_name, username):
    '''
    Loads the configuration from preg registry into a dictionary
    '''
    dd = dict()
    dd_win_style = dict()
    for i in pregfile.entries:
        # Skip this entry if the valuename starts with '**del'
        if i.valuename.startswith('**del'):
            continue
        valuename = convert_string_dconf(i.valuename)
        if i.valuename != i.data:
            if i.keyname.replace('\\', '/') in dd:
                # If the key exists in dd, update its value with the new key-value pair
                dd[i.keyname.replace('\\', '/')].update({valuename.replace('\\', '/'):i.data})
                dd_win_style[i.keyname].update({valuename:i.data})
            else:
                # If the key does not exist in dd, create a new key-value pair
                dd[i.keyname.replace('\\', '/')] = {valuename.replace('\\', '/'):i.data}
                dd_win_style[i.keyname] = {valuename:i.data}
        else:
            # If the value name is the same as the data,
            # split the keyname and add the data to the appropriate location in dd.
            all_list_key = i.keyname.split('\\')
            dd_target = dd.setdefault('/'.join(all_list_key[:-1]),{})
            dd_target.setdefault(all_list_key[-1], []).append(i.data)

            dd_target_win = dd_win_style.setdefault('\\'.join(all_list_key[:-1]),{})
            dd_target_win.setdefault(all_list_key[-1], []).append(i.data)
    # Update the global registry dictionary with the contents of dd
    add_to_dict(pathfile, policy_name, username)
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
    logdata = dict()
    logdata['path'] = filename
    log('D209', logdata)
    Dconf_registry.dconf_update()

def convert_string_dconf(input_string):
    # Check if the input string contains '%semicolon%'
    if '%semicolon%' in input_string:
        # If it contains, replace '%semicolon%' with ';'
        output_string = input_string.replace('%semicolon%', ';')
    else:
        # If it doesn't contain, replace ';' with '%semicolon%'
        output_string = input_string.replace(';', '%semicolon%')

    return output_string

def remove_empty_values(input_list):
    return list(filter(None, input_list))

def flatten_dictionary(input_dict, result=None, current_key=''):
    if result is None:
        result = {}

    for key, value in input_dict.items():
        new_key = f"{current_key}/{key}" if current_key else key

        if isinstance(value, dict):
            flatten_dictionary(value, result, new_key)
        else:
            result[new_key] = value

    return result

def get_dconf_envprofile():
    dconf_envprofile = {'default': {'DCONF_PROFILE': 'default'},
                    'local': {'DCONF_PROFILE': 'local'},
                    'system': {'DCONF_PROFILE': 'system'}
                    }

    if Dconf_registry._envprofile:
        return dconf_envprofile.get(Dconf_registry._envprofile, dconf_envprofile['system'])

    if not Dconf_registry._username:
        return dconf_envprofile['system']

    profile = '/run/dconf/user/{}'.format(get_uid_by_username(Dconf_registry._username))
    return {'DCONF_PROFILE': profile}
