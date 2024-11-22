#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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

import jinja2
import os
import subprocess
from pathlib import Path
import string

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.util import get_homedir
from util.logging import log

def storage_get_drives(storage, sid):
    drives = storage.get_drives(sid)
    drive_list = list()

    for drv_obj in drives:
        drive_list.append(drv_obj)

    return drive_list


def add_line_if_missing(filename, ins_line):
    with open(filename, 'r+') as f:
        for line in f:
            if ins_line == line.strip():
                break
        else:
            f.write(ins_line + '\n')
            f.flush()

def remove_chars_before_colon(input_string):
    if ":" in input_string:
        colon_index = input_string.index(":")
        result_string = input_string[colon_index + 1:]
        return result_string
    else:
        return input_string

def remove_escaped_quotes(input_string):
    result_string = input_string.replace('"', '').replace("'", '')
    return result_string


class Drive_list:
    __alphabet = string.ascii_uppercase
    def __init__(self):
        self.dict_drives = dict()

    def __get_letter(self, letter):
        slice_letters = set(self.__alphabet[self.__alphabet.find(letter) + 1:]) - set(self.dict_drives.keys())
        free_letters = sorted(slice_letters)
        if free_letters:
            return free_letters[0]
        else:
            return None

    def append(self, drive:dict):
        cur_dir = drive['dir']
        if cur_dir not in set(self.dict_drives.keys()):
            if drive['action'] == 'D':
                return
            self.dict_drives[cur_dir] = drive
            return

        else:
            if drive['action'] == 'C':
                if drive['useLetter'] == '1':
                    return
                else:
                    new_dir = self.__get_letter(cur_dir)
                    if not new_dir:
                        return
                    drive['dir'] = new_dir
                    self.dict_drives[new_dir] = drive
                    return

            if drive['action'] == 'U':
                self.dict_drives[cur_dir]['thisDrive'] = drive['thisDrive']
                self.dict_drives[cur_dir]['allDrives'] = drive['allDrives']
                self.dict_drives[cur_dir]['label'] = drive['label']
                self.dict_drives[cur_dir]['persistent'] = drive['persistent']
                self.dict_drives[cur_dir]['useLetter'] = drive['useLetter']
                return

            if drive['action'] == 'R':
                self.dict_drives[cur_dir] = drive
                return
            if drive['action'] == 'D':
                if drive['useLetter'] == '1':
                    self.dict_drives.pop(cur_dir, None)
                else:
                    keys_set = set(self.dict_drives.keys())
                    slice_letters = set(self.__alphabet[self.__alphabet.find(cur_dir):])
                    for letter_dir in (keys_set & slice_letters):
                        self.dict_drives.pop(letter_dir, None)

    def __call__(self):
        return list(self.dict_drives.values())

    def len(self):
        return len(self.dict_drives)

class cifs_applier(applier_frontend):
    __module_name = 'CIFSApplier'
    __module_enabled = True
    __module_experimental = False

    def __init__(self, storage, sid):
        self.applier_cifs = cifs_applier_user(storage, sid, None)
        self.__module_enabled = check_enabled(
              storage
            , self.__module_name
            , self.__module_experimental
        )

    def apply(self):
        if self.__module_enabled:
            log('D179')
            self.applier_cifs._admin_context_apply()
        else:
            log('D180')

class cifs_applier_user(applier_frontend):
    __module_name = 'CIFSApplierUser'
    __module_enabled = True
    __module_experimental = False
    __auto_file = '/etc/auto.master'
    __auto_dir = '/etc/auto.master.gpupdate.d'
    __template_path = '/usr/share/gpupdate/templates'
    __template_mountpoints = 'autofs_mountpoints.j2'
    __template_identity = 'autofs_identity.j2'
    __template_auto = 'autofs_auto.j2'
    __template_mountpoints_hide = 'autofs_mountpoints_hide.j2'
    __template_auto_hide = 'autofs_auto_hide.j2'
    __enable_home_link = 'Software\\BaseALT\\Policies\\GPUpdate\\DriveMapsHome'
    __enable_home_link_user = 'Software\\BaseALT\\Policies\\GPUpdate\\DriveMapsHomeUser'
    __target_mountpoint = '/media/gpupdate'
    __target_mountpoint_user = '/run/media'
    __mountpoint_dirname = 'drives.system'
    __mountpoint_dirname_user = 'drives'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.state_home_link = False
        self.state_home_link_user = False

        if username:
            self.home = self.__target_mountpoint_user + '/' + username
            self.state_home_link = self.check_enable_home_link(self.__enable_home_link)
            self.state_home_link_user = self.check_enable_home_link(self.__enable_home_link_user)
        else:
            self.home = self.__target_mountpoint

        conf_file = '{}.conf'.format(sid)
        conf_hide_file = '{}_hide.conf'.format(sid)
        autofs_file = '{}.autofs'.format(sid)
        autofs_hide_file = '{}_hide.autofs'.format(sid)
        cred_file = '{}.creds'.format(sid)

        self.auto_master_d = Path(self.__auto_dir)

        self.user_config = self.auto_master_d / conf_file
        self.user_config_hide = self.auto_master_d / conf_hide_file
        if os.path.exists(self.user_config.resolve()):
            self.user_config.unlink()
        if os.path.exists(self.user_config_hide.resolve()):
            self.user_config_hide.unlink()
        self.user_autofs = self.auto_master_d / autofs_file
        self.user_autofs_hide = self.auto_master_d / autofs_hide_file
        if os.path.exists(self.user_autofs.resolve()):
            self.user_autofs.unlink()
        if os.path.exists(self.user_autofs_hide.resolve()):
            self.user_autofs_hide.unlink()
        self.user_creds = self.auto_master_d / cred_file

        if username:
            self.mntTarget = self.__mountpoint_dirname_user
        else:
            self.mntTarget = self.__mountpoint_dirname

        self.mount_dir = Path(os.path.join(self.home))
        self.drives = storage_get_drives(self.storage, self.sid)

        self.template_loader = jinja2.FileSystemLoader(searchpath=self.__template_path)
        self.template_env = jinja2.Environment(loader=self.template_loader)

        self.template_mountpoints = self.template_env.get_template(self.__template_mountpoints)
        self.template_indentity = self.template_env.get_template(self.__template_identity)
        self.template_auto = self.template_env.get_template(self.__template_auto)

        self.template_mountpoints_hide = self.template_env.get_template(self.__template_mountpoints_hide)
        self.template_auto_hide = self.template_env.get_template(self.__template_auto_hide)

        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def check_enable_home_link(self, enable_home_link):
        if self.storage.get_hkcu_entry(self.sid, enable_home_link):
            data = self.storage.get_hkcu_entry(self.sid, enable_home_link).data
            return bool(int(data)) if data else None
        else:
            return False

    def user_context_apply(self):
        '''
        Nothing to implement.
        '''
        pass

    def _admin_context_apply(self):
        # Create /etc/auto.master.gpupdate.d directory
        self.auto_master_d.mkdir(parents=True, exist_ok=True)
        # Create user's destination mount directory
        self.mount_dir.mkdir(parents=True, exist_ok=True)

        # Add pointer to /etc/auto.master.gpiupdate.d in /etc/auto.master
        auto_destdir = '+dir:{}'.format(self.__auto_dir)
        add_line_if_missing(self.__auto_file, auto_destdir)

        # Collect data for drive settings
        drive_list = Drive_list()
        for drv in self.drives:
            drive_settings = dict()
            drive_settings['dir'] = drv.dir
            drive_settings['login'] = drv.login
            drive_settings['password'] = drv.password
            drive_settings['path'] = remove_chars_before_colon(drv.path.replace('\\', '/'))
            drive_settings['action'] = drv.action
            drive_settings['thisDrive'] = drv.thisDrive
            drive_settings['allDrives'] = drv.allDrives
            drive_settings['label'] = remove_escaped_quotes(drv.label)
            drive_settings['persistent'] = drv.persistent
            drive_settings['useLetter'] = drv.useLetter

            drive_list.append(drive_settings)

        if drive_list.len() > 0:
            mount_settings = dict()
            mount_settings['drives'] = drive_list()
            mount_text = self.template_mountpoints.render(**mount_settings)

            mount_text_hide = self.template_mountpoints_hide.render(**mount_settings)

            with open(self.user_config.resolve(), 'w') as f:
                f.truncate()
                f.write(mount_text)
                f.flush()

            with open(self.user_config_hide.resolve(), 'w') as f:
                f.truncate()
                f.write(mount_text_hide)
                f.flush()

            autofs_settings = dict()
            autofs_settings['home_dir'] = self.home
            autofs_settings['mntTarget'] = self.mntTarget
            autofs_settings['mount_file'] = self.user_config.resolve()
            autofs_text = self.template_auto.render(**autofs_settings)

            with open(self.user_autofs.resolve(), 'w') as f:
                f.truncate()
                f.write(autofs_text)
                f.flush()

            autofs_settings['mount_file'] = self.user_config_hide.resolve()
            autofs_text = self.template_auto_hide.render(**autofs_settings)
            with open(self.user_autofs_hide.resolve(), 'w') as f:
                f.truncate()
                f.write(autofs_text)
                f.flush()

            if self.username:
                self.update_drivemaps_home_links()

            subprocess.check_call(['/bin/systemctl', 'restart', 'autofs'])

    def update_drivemaps_home_links(self):
        dUser = Path(get_homedir(self.username)+'/net.' + self.__mountpoint_dirname_user)
        dUserHide = Path(get_homedir(self.username)+'/.net.' + self.__mountpoint_dirname_user)

        if self.state_home_link_user:
            dUserMountpoint = Path(self.home).joinpath(self.__mountpoint_dirname_user)
            dUserMountpointHide = Path(self.home).joinpath('.' + self.__mountpoint_dirname_user)

            if not dUser.exists():
                try:
                    os.symlink(dUserMountpoint, dUser, True)
                except  Exception as exc:
                    log('D194', {'exc': exc})

            if not dUserHide.exists():
                try:
                    os.symlink(dUserMountpointHide, dUserHide, True)
                except  Exception as exc:
                    log('D196', {'exc': exc})
        else:
            if dUser.is_symlink() and dUser.owner() == 'root':
                dUser.unlink()
            if dUserHide.is_symlink() and dUserHide.owner() == 'root':
                dUserHide.unlink()

        dMachine = Path(get_homedir(self.username)+'/net.' + self.__mountpoint_dirname)
        dMachineHide = Path(get_homedir(self.username)+'/.net.' + self.__mountpoint_dirname)

        if self.state_home_link:
            dMachineMountpoint = Path(self.__target_mountpoint).joinpath(self.__mountpoint_dirname)
            dMachineMountpointHide = Path(self.__target_mountpoint).joinpath('.' + self.__mountpoint_dirname)

            if not dMachine.exists():
                try:
                    os.symlink(dMachineMountpoint, dMachine, True)
                except  Exception as exc:
                    log('D195', {'exc': exc})

            if not dMachineHide.exists():
                try:
                    os.symlink(dMachineMountpointHide, dMachineHide, True)
                except  Exception as exc:
                    log('D197', {'exc': exc})
        else:
            if dMachine.is_symlink() and dMachine.owner() == 'root':
                dMachine.unlink()
            if dMachineHide.is_symlink() and dMachineHide.owner() == 'root':
                dMachineHide.unlink()

    def admin_context_apply(self):
        if self.__module_enabled:
            log('D146')
            self._admin_context_apply()
        else:
            log('D147')

