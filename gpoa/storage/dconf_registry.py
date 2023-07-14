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

class Dconf_registry():
    '''
    A class variable that represents a global registry dictionary shared among instances of the class
    '''
    global_registry_dict = dict({'Software/BaseALT/Policies/ReadQueue':{}})


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
    add_to_dict(Dconf_registry.global_registry_dict['Software/BaseALT/Policies/ReadQueue'], pathfile)
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
                file.write(f'{key} = "{value}"\n')
            file.write('\n')
