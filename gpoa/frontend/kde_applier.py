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

from .applier_frontend import applier_frontend, check_enabled
from util.logging import log
from util.util import get_homedir, string_to_literal_eval

import os
import subprocess

widget_utilities = {
            'colorscheme': 'plasma-apply-colorscheme',
            'cursortheme': 'plasma-apply-cursortheme',
            'desktoptheme': 'plasma-apply-desktoptheme',
            'wallpaperimage': 'plasma-apply-wallpaperimage'
        }

class kde_applier(applier_frontend):
    __module_name = 'KdeApplier'
    __module_experimental = False
    __module_enabled = True
    __hklm_branch = 'Software\\BaseALT\\Policies\\KDE\\'
    __hklm_lock_branch = 'Software\\BaseALT\\Policies\\KDELocks\\'

    def __init__(self, storage):
        self.storage = storage
        self.locks_dict = {}
        self.locks_data_dict = {}
        self.all_kde_settings = {}
        kde_filter = '{}%'.format(self.__hklm_branch)
        locks_filter = '{}%'.format(self.__hklm_lock_branch)
        self.locks_settings = self.storage.filter_hklm_entries(locks_filter)
        self.kde_settings = self.storage.filter_hklm_entries(kde_filter)
        self.all_kde_settings = {}

        self.__module_enabled = check_enabled(
            self.storage,
            self.__module_name,
            self.__module_experimental
        )

    def admin_context_apply(self):
        '''
        Change settings applied in admin context
        '''

    def user_context_apply(self):
        '''
        Change settings applied in user context
        '''

    def apply(self):
        if self.__module_enabled:
            log('D198')
            parse_key(self.locks_settings, self.kde_settings, self.all_kde_settings, self.locks_data_dict)
            apply(self.all_kde_settings, self.locks_data_dict)
        else:
            log('D199')

class kde_applier_user(applier_frontend):
    __module_name = 'KdeApplierUser'
    __module_experimental = False
    __module_enabled = True
    __hkcu_branch = 'Software\\BaseALT\\Policies\\KDE\\'
    __hkcu_lock_branch = 'Software\\BaseALT\\Policies\\KDELocks\\'
    widget_utilities = {
            'colorscheme': 'plasma-apply-colorscheme',
            'cursortheme': 'plasma-apply-cursortheme',
            'desktoptheme': 'plasma-apply-desktoptheme',
            'wallpaperimage': 'plasma-apply-wallpaperimage'
        }


    def __init__(self, storage, sid=None, username=None):
        self.storage = storage
        self.username = username
        self.sid = sid
        self.locks_dict = {}
        self.locks_data_dict = {}
        self.all_kde_settings = {}
        kde_filter = '{}%'.format(self.__hkcu_branch)
        locks_filter = '{}%'.format(self.__hkcu_lock_branch) 
        self.locks_settings = self.storage.filter_hkcu_entries(self.sid, locks_filter)
        self.kde_settings = self.storage.filter_hkcu_entries(self.sid, kde_filter)
        self.__module_enabled = check_enabled(
            self.storage,
            self.__module_name,
            self.__module_experimental
        )


    def admin_context_apply(self):
        '''
        Change settings applied in admin context
        '''

    def user_context_apply(self):
        '''
        Change settings applied in user context
        '''
        if self.__module_enabled:
            log('D200')
            parse_key(self.locks_settings, self.kde_settings, self.all_kde_settings, self.locks_data_dict, self.username)
            apply(self.all_kde_settings, self.locks_data_dict, self.username)
        else:
            log('D201')

def parse_key(locks_settings, kde_settings, all_kde_dict, locks_data_dict, username = None):
    '''
    Method used to parse hive_key
    '''
    locks_dict = {}
    for locks in locks_settings:
        locks_dict[locks.valuename] = locks.data
    for setting in kde_settings:
        valuename = setting.valuename.split('.')
        file = valuename[0]
        value = valuename[1]
        data = string_to_literal_eval(setting.data)
        valuename_for_dict = f"{file}.{value}"
        type_of_lock = locks_dict[valuename_for_dict]
        if type_of_lock == '1':
            locks_data_dict[str(data)] = type_of_lock
        if file == 'plasma' and username is not None:
            apply_for_widget(value, widget_utilities, username, data)
        else:
            update_dict(all_kde_dict, {file : data})

def apply(all_kde_dict, locks_data_dict, username = None):
    '''
    Method for changing configuration files
    '''
    for file_name, sections in all_kde_dict.items():
        if username is not None:
            file_name = os.path.expanduser(f'{get_homedir(username)}/.config/{file_name}')
        else:
            file_name = f"/etc/xdg/{file_name}"
            if os.path.exists(file_name):
                os.remove(file_name)
        with open(file_name, 'a') as file:
            logdata = dict()
            logdata['file'] = file_name
            log('D202', logdata)
            for section, keys in sections.items():
                result = { section : keys}
                file.write(f"[{section}]\n")
                if str(result) in locks_data_dict:
                    for key, value in keys.items():
                        file.write(f"{key}[$i]={value}\n")
                else:
                    for key, value in keys.items():
                        file.write(f"{key}={value}\n")
            file.write('\n')

def apply_for_widget(value, widget_utilities, username, data):
    '''
    Method for changing graphics settings in plasma context
    '''
    try:
            if value in widget_utilities:
                os.environ["XDG_DATA_DIRS"] = f"{get_homedir(username)}.local/share/flatpak/exports/share:/var/lib/flatpak \
                    /exports/share:/usr/local/share:/usr/share/kf5:/usr/share:/var/lib/snapd/desktop"
                    #Variable for system detection of directories before files with .colors extension
                os.environ["DISPLAY"] = ":0"
                    #Variable for command execution plasma-apply-colorscheme
                os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"#plasma-apply-wallpaperimage
                os.environ["PATH"] = f"{get_homedir(username)}/bin:/usr/local/bin:/usr/lib/kf5/bin:/usr/bin:/bin:/usr/games: \
                    /var/lib/snapd/snap/bin"
                    #environment variable for accessing binary files without hard links
                command = [f"{widget_utilities[value]}", f"{data}"]
                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = proc.communicate()
                if proc.returncode == 0:
                    output = stdout.decode("utf-8").strip()
                    log('D203')
                else:
                    error = stderr.decode("utf-8").strip()
                    log('E66')
            else:
                pass
    except OSError as e:
        log('E67')

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
