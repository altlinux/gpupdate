#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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

import os
import pwd
import re
import shutil
import subprocess
from pathlib import Path

try:
    import dbus
except ImportError:
    dbus = None
from ..util.exceptions import NotUNCPathError
from ..util.logging import log
from ..util.util import get_homedir

from .applier_frontend import applier_frontend, DualContextApplier, check_enabled
from ..applier_result import ApplierResult, ItemStatus, RESULT_SUCCESS

KDE_TOOL_PATH = '/usr/lib/kf5/bin:/usr/lib/kf6/bin:/usr/bin'


class kde_applier(applier_frontend):
    __module_name = 'KdeApplier'
    __module_experimental = True
    __module_enabled = False
    __hklm_branch = 'Software/BaseALT/Policies/KDE/'
    __hklm_lock_branch = 'Software/BaseALT/Policies/KDELocks/'

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
            return ApplierResult.applied('kde', [ItemStatus(key='kde_settings', action='set', result=RESULT_SUCCESS)])
        else:
            log('D199')
            return ApplierResult.skipped('kde')

class kde_applier_user(DualContextApplier):
    __module_name = 'KdeApplierUser'
    __module_experimental = True
    __module_enabled = False
    kde_version = None
    __hkcu_branch = 'Software/BaseALT/Policies/KDE'
    __hkcu_lock_branch = 'Software/BaseALT/Policies/KDELocks'
    __plasma_update_entry = 'Software/BaseALT/Policies/KDE/Plasma/Update'

    def __init__(self, storage, username=None, file_cache = None):
        self.storage = storage
        self.username = username
        self.file_cache = file_cache
        self.locks_dict = {}
        self.locks_data_dict = {}
        self.all_kde_settings = {}
        kde_filter = '{}%'.format(self.__hkcu_branch)
        locks_filter = '{}%'.format(self.__hkcu_lock_branch)
        self.locks_settings = self.storage.filter_hkcu_entries(locks_filter)
        self.plasma_update = self.storage.get_entry(
            self.__plasma_update_entry,
            dictionary=self.storage.global_registry_dict)
        try:
            self.plasma_update_flag = int(self.plasma_update.data)
        except (TypeError, ValueError, AttributeError):
            self.plasma_update_flag = 0
        self.kde_settings = self.storage.filter_hkcu_entries(kde_filter)
        self.__module_enabled = check_enabled(
            self.storage,
            self.__module_name,
            self.__module_experimental
        )

    def admin_context_apply(self):
        try:
            for setting in self.kde_settings:
                file_name = setting.keyname.split("/")[-2]
                section = setting.keyname.split("/")[-1]
                if file_name == 'wallpaper':
                    self.file_cache.store(setting.data)
                if (file_name, section, setting.valuename) == ('kscreenlockerrc',
                                                               'Greeter)(Wallpaper)(org.kde.image)(General',
                                                               'Image'):
                    self.file_cache.store(setting.data)
        except Exception as exc:
            logdata = {'exc': exc}

    def user_context_apply(self):
        if self.__module_enabled:
            log('D200')
            if not self.kde_settings:
                return ApplierResult.applied('kde_user')
            if kde_applier_user.kde_version is None:
                kde_applier_user.kde_version = get_kde_version()
            if kde_applier_user.kde_version is None:
                return ApplierResult.failed('kde_user', 'Unable to determine KDE configuration tool version')
            try:
                create_dict(self.kde_settings, self.all_kde_settings, self.locks_settings, self.locks_dict, self.file_cache, self.username, self.plasma_update_flag)
                apply(self.all_kde_settings, self.locks_dict, self.username)
            except Exception as exc:
                return ApplierResult.failed('kde_user', str(exc))
            return ApplierResult.applied('kde_user', [ItemStatus(key='kde_settings', action='set', result=RESULT_SUCCESS)])
        else:
            log('D201')
            return ApplierResult.skipped('kde_user')

dbus_methods_mapping = {
    'kscreenlockerrc': {
        'dbus_service': 'org.kde.screensaver',
        'dbus_path': '/ScreenSaver',
        'dbus_interface': 'org.kde.screensaver',
        'dbus_method': 'configure'
    },
    'wallpaper': {
        'dbus_service': 'org.freedesktop.systemd1',
        'dbus_path': '/org/freedesktop/systemd1',
        'dbus_interface': 'org.freedesktop.systemd1.Manager',
        'dbus_method': 'RestartUnit',
        'dbus_args': ['plasma-plasmashell.service', 'replace']
    }
}

def get_kde_version():
    try:
        kinfo_path = shutil.which('kinfo', path=KDE_TOOL_PATH)
        if not kinfo_path:
            raise FileNotFoundError("Unable to find kinfo")
        env = os.environ.copy()
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        # kinfo uses Qt even for text output. Do not require a display at login.
        env['QT_QPA_PLATFORM'] = 'offscreen'
        output = subprocess.check_output([kinfo_path], text=True, env=env, timeout=15)
        for line in output.splitlines():
            if "KDE Frameworks Version" in line:
                frameworks_version = line.split(":", 1)[1].strip()
                major_frameworks_version = int(frameworks_version.split(".")[0])
                if major_frameworks_version in (5, 6) and shutil.which(
                        f'kwriteconfig{major_frameworks_version}', path=KDE_TOOL_PATH):
                    return major_frameworks_version
    except Exception as exc:
        log('D', {'message': 'KDE version probe failed', 'plugin': 'KdeApplier',
                  'data': {'exc': str(exc)}})
    # Minimal installations may lack kinfo or the offscreen Qt plugin. Only
    # select an installed writer when there is no ambiguity between KDE 5/6.
    versions = [version for version in (5, 6)
                if shutil.which(f'kwriteconfig{version}', path=KDE_TOOL_PATH)]
    return versions[0] if len(versions) == 1 else None


def create_dict(kde_settings, all_kde_settings, locks_settings, locks_dict, file_cache = None, username = None, plasmaupdate = False):
        for locks in locks_settings:
            locks_dict[locks.valuename] = locks.data
        for setting in kde_settings:
            try:
                file_name, section, value = setting.keyname.split("/")[-2], setting.keyname.split("/")[-1], setting.valuename
                data = setting.data
                if file_name == 'wallpaper':
                    apply_for_wallpaper(data, file_cache, username, plasmaupdate)
                else:
                    if (file_name, section, value) == ('kscreenlockerrc',
                                                       'Greeter)(Wallpaper)(org.kde.image)(General',
                                                       'Image') and file_cache is not None:
                        resolved = file_cache.get(data)
                        if resolved:
                            data = resolved
                    all_kde_settings.setdefault(file_name, {}).setdefault(section, {})[value] = data
            except Exception as exc:
                logdata = {'file_name': file_name,
                           'section': section,
                           'value': value,
                           'data': data,
                           'exc': exc}
                log('W16', logdata)

def apply(all_kde_settings, locks_dict, username = None):
    logdata = {}
    modified_files = set()
    errors = []
    if username is None:
        system_path_settings = '/etc/xdg/'
        system_files = [
            "baloofilerc",
            "kcminputrc",
            "kded_device_automounterrc",
            "kdeglobals",
            "kscreenlockerrc",
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
            file_path = f'{system_path_settings}{file_name}'
            with open(file_path, 'w') as file:
                for section, keys in sections.items():
                    section = section.replace(')(', '][')
                    file.write(f'[{section}]\n')
                    for key, value in keys.items():
                        lock = f"{file_name}.{section}.{key}".replace('][', ')(')
                        if locks_dict.get(lock) == 1:
                            file.write(f'{key}[$i]={value}\n')
                        else:
                            file.write(f'{key}={value}\n')
                    file.write('\n')
            modified_files.add(file_name)
    else:
        if kde_applier_user.kde_version not in (5, 6):
            raise RuntimeError('Unable to determine KDE configuration tool version')
        for file_name, sections in all_kde_settings.items():
            path = f'{get_homedir(username)}/.config/{file_name}'
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            if not os.path.exists(path):
                Path(path).touch()
            else:
                pass
            for section, keys in sections.items():
                for key, value in keys.items():
                    value = str(value)
                    lock = f"{file_name}.{section}.{key}"
                    if lock in locks_dict and locks_dict[lock] == 1:
                        command = [
                            f'kwriteconfig{kde_applier_user.kde_version}',
                            '--file', file_name,
                            '--group', section,
                            '--key', key +'/$i/',
                            '--type', 'string',
                            value
                        ]
                    else:
                        command = [
                            f'kwriteconfig{kde_applier_user.kde_version}',
                            '--file', file_name,
                            '--group', section,
                            '--key', key,
                            '--type', 'string',
                            value
                        ]
                    try:
                        clear_locks_settings(username, file_name, key)
                        env_path = dict(os.environ)
                        env_path['PATH'] = KDE_TOOL_PATH
                        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_path, timeout=15)
                    except Exception as exc:
                            logdata = {'command': command, 'exc': exc}
                            log('W22', logdata)
                            errors.append(f'{file_name}/{section}/{key}: {exc}')
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
                errors.append(f'{file_name}: {exc}')
            modified_files.add(file_name)
    for file_name in modified_files:
        call_dbus_method(file_name, username)
    if errors:
        raise RuntimeError('; '.join(errors))

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
            logdata = {'line': line.strip()}
            log('I10', logdata)

def apply_for_wallpaper(data, file_cache, username, plasmaupdate):
    '''
    Method to change wallpaper
    '''
    logdata = {}
    path_to_wallpaper = f'{get_homedir(username)}/.config/plasma-org.kde.plasma.desktop-appletsrc'
    id_desktop = get_id_desktop(path_to_wallpaper)
    try:
        try:
            data = str(file_cache.get(data))
        except NotUNCPathError:
            data = str(data)

        with open(path_to_wallpaper, 'r') as file:
            current_wallpaper = file.read()
        match = re.search(rf'\[Containments\]\[{id_desktop}\]\[Wallpaper\]\[org\.kde\.image\]\[General\]\s+Image=(.*)', current_wallpaper)
        if match:
            current_wallpaper_path = match.group(1)
            flag = (current_wallpaper_path == data)
        else:
            flag = False

        env_path = dict(os.environ)
        env_path["LANGUAGE"] = env_path.get("LANG", "").split(".")[0]
        env_path["XDG_DATA_DIRS"] = "/usr/share/kf5:"
        env_path["DISPLAY"] = ":0"
        env_path["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        env_path['PATH'] = KDE_TOOL_PATH
        env_path["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"
        if not flag:
            if os.path.isfile(path_to_wallpaper):
                command = [
                    f'kwriteconfig{kde_applier_user.kde_version}',
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
                    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_path, timeout=15)
                except Exception as exc:
                        logdata = {'command': command, 'exc': exc}
                        log('E68', logdata)
                if plasmaupdate == 1:
                    call_dbus_method("wallpaper", username)
        else:
            logdata = {'file': path_to_wallpaper}
            log('W21', logdata)
    except OSError as exc:
        logdata = {'exc': exc}
        log('W17', logdata)
    except Exception as exc:
        logdata = {'exc': exc}
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
        return match.group(1) if match else None
    except Exception as exc:
        log('D271', {'path': path_to_wallpaper, 'exc': str(exc)})
        return None

def call_dbus_method(file_name, username=None):
    '''
    Method to call D-Bus method based on the file name
    '''
    if username is None or file_name not in dbus_methods_mapping:
        return
    if dbus is None:
        return
    try:
        uid = pwd.getpwnam(username).pw_uid
    except KeyError:
        return
    bus_socket = f'/run/user/{uid}/bus'
    if not os.path.exists(bus_socket):
        return
    config = dbus_methods_mapping[file_name]
    try:
        session_bus = dbus.bus.BusConnection(f'unix:path={bus_socket}')
        if config['dbus_service'] not in session_bus.list_names():
            return
        dbus_object = session_bus.get_object(config['dbus_service'], config['dbus_path'])
        dbus_iface = dbus.Interface(dbus_object, config['dbus_interface'])
        if 'dbus_args' in config:
            getattr(dbus_iface, config['dbus_method'])(*config['dbus_args'])
        else:
            getattr(dbus_iface, config['dbus_method'])()
    except dbus.exceptions.DBusException as exc:
        log('W', {'message': 'KDE D-Bus reload failed',
                  'plugin': 'KdeApplier',
                  'data': {'file': file_name, 'error': str(exc)}})
