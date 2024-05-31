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
from util.util import get_homedir
from util.exceptions import NotUNCPathError
import os
import subprocess
import re
import dbus

class kde_applier(applier_frontend):
    __module_name = 'KdeApplier'
    __module_experimental = True
    __module_enabled = False
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

    def apply(self):
        if self.__module_enabled:
            log('D198')
            create_dict(self.kde_settings, self.all_kde_settings, self.locks_settings, self.locks_dict)
            apply(self.all_kde_settings, self.locks_dict)
        else:
            log('D199')

class kde_applier_user(applier_frontend):
    __module_name = 'KdeApplierUser'
    __module_experimental = True
    __module_enabled = False
    __hkcu_branch = 'Software\\BaseALT\\Policies\\KDE\\'
    __hkcu_lock_branch = 'Software\\BaseALT\\Policies\\KDELocks\\'

    def __init__(self, storage, sid=None, username=None, file_cache = None):
        self.storage = storage
        self.username = username
        self.sid = sid
        self.file_cache = file_cache
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
        pass

    def user_context_apply(self):
        '''
        Change settings applied in user context
        '''
        if self.__module_enabled:
            log('D200')
            create_dict(self.kde_settings, self.all_kde_settings, self.locks_settings, self.locks_dict, self.file_cache, self.username)
            apply(self.all_kde_settings, self.locks_dict, self.username)
        else:
            log('D201')

def create_dict(kde_settings, all_kde_settings, locks_settings, locks_dict, file_cache = None, username = None):
        for locks in locks_settings:
            locks_dict[locks.valuename] = locks.data
        for setting in kde_settings:
            try:
                file_name, section, value = setting.keyname.split("/")[-2], setting.keyname.split("/")[-1], setting.valuename
                data = setting.data
                if file_name == 'wallpaper':
                    apply_for_wallpaper(data, file_cache, username)
                else:
                    if file_name not in all_kde_settings:
                        all_kde_settings[file_name] = {}
                    if section not in all_kde_settings[file_name]:
                        all_kde_settings[file_name][section] = {}
                    all_kde_settings[file_name][section][value] = data

            except Exception as exc:
                logdata = dict()
                logdata['file_name'] = file_name
                logdata['section'] = section
                logdata['value'] = value
                logdata['data'] = data
                logdata['exc'] = exc
                log('W16', logdata)

def apply(all_kde_settings, locks_dict, username = None):
    logdata = dict()
    if username is None:
        system_path_settings = '/etc/xdg/'
        system_files = [
            "baloofilerc",
            "kcminputrc",
            "kded_device_automounterrc",
            "kdeglobals",
            "ksplashrc",
            "kwinrc",
            "plasma-localerc",
            "plasmarc",
            "powermanagementprofilesrc"
        ]
        for file in system_files:
            file_to_remove = f'{system_path_settings}{file}'
            if os.path.exists(file_to_remove):
                os.remove(file_to_remove)
        for file_name, sections in all_kde_settings.items():
            file_path = f'{system_path_settings{file_name}'
            with open(file_path, 'w') as file:
                for section, keys in sections.items():
                    section = section.replace(')(', '][')
                    file.write(f'[{section}]\n')
                    for key, value in keys.items():
                        lock = f"{file_name}.{section}.{key}".replace('][', ')(')
                        if lock in locks_dict and locks_dict[lock] == 1:
                            file.write(f'{key}[$i]={value}\n')
                        else:
                            file.write(f'{key}={value}\n')
                    file.write('\n')
    else:
        for file_name, sections in all_kde_settings.items():
            path = f'{get_homedir(username)}/.config/{file_name}'
            if not os.path.exists(path):
                open(path, 'a').close()
            else:
                pass
            for section, keys in sections.items():
                for key, value in keys.items():
                    lock = f"{file_name}.{section}.{key}"
                    if lock in locks_dict and locks_dict[lock] == 1:
                        command = [
                            'kwriteconfig5',
                            '--file', file_name,
                            '--group', section,
                            '--key', key +'/$i/',
                            '--type', 'string',
                            value
                        ]
                    else:
                        command = [
                            'kwriteconfig5',
                            '--file', file_name,
                            '--group', section,
                            '--key', key,
                            '--type', 'string',
                            value
                        ]
                    try:
                        clear_locks_settings(username, file_name, key)
                        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    except:
                            logdata['command'] = command
                            log('W22', logdata)
            new_content = []
            file_path = f'{get_homedir(username)}/.config/{file_name}'
            try:
                with open(file_path, 'r') as file:
                    for line in file:
                        line = line.replace('/$i/', '[$i]').replace(')(', '][')
                        new_content.append(line)
                with open(file_path, 'w') as file:
                    file.writelines(new_content)
                logdata['file'] = file_name
                log('D202', logdata)
            except Exception as exc:
                logdata['exc'] = exc
                log('W19', logdata)

def clear_locks_settings(username, file_name, key):
    '''
    Method to remove old locked settings
    '''
    file_path = f'{get_homedir(username)}/.config/{file_name}'
    with open(file_path, 'r') as file:
        lines = file.readlines()
    with open(file_path, 'w') as file:
        for line in lines:
            if f'{key}[$i]=' not in line:
                file.write(line)
    for line in lines:
        if f'{key}[$i]=' in line:
            logdata = dict()
            logdata['line'] = line.strip()
            log('I10', logdata)

def apply_for_wallpaper(data, file_cache, username):
    '''
    Method to change wallpaper
    '''
    logdata = dict()
    path_to_wallpaper = f'{get_homedir(username)}/.config/plasma-org.kde.plasma.desktop-appletsrc'
    try:
        try:
            file_cache.store(data)
            data = file_cache.get(data)
        except NotUNCPathError:
            data = data
        os.environ["XDG_DATA_DIRS"] = "/usr/share/kf5:"
            #Variable for system detection of directories before files with .colors extension
        os.environ["DISPLAY"] = ":0"
            #Variable for command execution plasma-apply-colorscheme
        os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"#plasma-apply-wallpaperimage
        os.environ["PATH"] = "/usr/lib/kf5/bin:"
            #environment variable for accessing binary files without hard links
        if os.path.isfile(path_to_wallpaper):
            id_desktop = get_id_desktop(path_to_wallpaper)
            command = [
                'kwriteconfig5',
                '--file', 'plasma-org.kde.plasma.desktop-appletsrc',
                '--group', 'Containments',
                '--group', id_desktop,
                '--group', 'Wallpaper',
                '--group', 'org.kde.image',
                '--group', 'General',
                '--key', 'Image',
                 '--type', 'string',
                data
                ]
            try:
                subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except:
                    logdata['command'] = command
                    log('E68', logdata)
            try:
                session_bus = dbus.SessionBus()
                plasma_shell = session_bus.get_object('org.kde.plasmashell', '/PlasmaShell', introspect='org.kde.PlasmaShell')
                plasma_shell_iface = dbus.Interface(plasma_shell, 'org.kde.PlasmaShell')
                plasma_shell_iface.refreshCurrentShell()
            except:
                pass
        else:
            logdata['file'] = path_to_wallpaper
            log('W21', logdata)
    except OSError as exc:
        logdata['exc'] = exc
        log('W17', logdata)
    except Exception as exc:
        logdata['exc'] = exc
        log('E67', logdata)

def get_id_desktop(path_to_wallpaper):
    '''
    Method for getting desktop id. It is currently accepted that this number is one of the sections in the configuration file.
    '''
    pattern = r'\[Containments\]\[(\d+)\][^\[]*activityId=([^\s]+)'
    try:
        with open(path_to_wallpaper, 'r') as file:
            file_content = file.read()
        match = re.search(pattern, file_content)
        if match:
            return match.group(1)
        else:
            return None
    except:
        return None
