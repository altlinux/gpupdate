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

import fileinput
import jinja2
import os
from pathlib import Path

from .applier_frontend import applier_frontend
from gpt.drives import json2drive
from util.util import get_homedir

def storage_get_drives(storage, sid):
    drives = storage.get_drives(sid)
    drive_list = list()

    for drv_obj in drives:
        drive_list.append(drv_obj)

    return drive_list


def add_line_if_missing(filename, ins_line):
    with open(filename, 'r+') as f:
        for line in f:
            if ins_line in line.strip():
                break
        else:
            f.write(ins_line)

class cifs_applier(applier_frontend):
    def __init__(self, storage):
        pass

    def apply(self):
        pass

class cifs_applier_user(applier_frontend):
    __auto_file = '/etc/auto.master'
    __auto_dir = '/etc/auto.master.gpupdate.d'
    __template_path = '/usr/share/gpupdate/templates'
    __template_mountpoints = 'autofs_mountpoints.j2'
    __template_identity = 'autofs_identity.j2'
    __template_auto = 'autofs_auto.j2'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

        self.home = get_homedir(username)
        conf_file = '{}.conf'.format(sid)
        autofs_file = '{}.autofs'.format(sid)
        cred_file = '{}.creds'.format(sid)

        self.auto_master_d = Path(self.__auto_dir)

        self.user_config = self.auto_master_d / conf_file
        self.user_autofs = self.auto_master_d / autofs_file
        self.user_creds = self.auto_master_d / cred_file

        self.mount_dir = Path(os.path.join(self.home, 'net'))
        self.drives = storage_get_drives(self.storage, self.sid)

        self.template_loader = jinja2.FileSystemLoader(searchpath=self.__template_path)
        self.template_env = jinja2.Environment(loader=self.template_loader)

        self.template_mountpoints = self.template_env.get_template(self.__template_mountpoints)
        self.template_indentity = self.template_env.get_template(self.__template_identity)
        self.template_auto = self.template_env.get_template(self.__template_auto)


    def user_context_apply(self):
        '''
        Nothing to implement.
        '''
        pass

    def admin_context_apply(self):
        # Create /etc/auto.master.gpupdate.d directory
        self.auto_master_d.mkdir(parents=True, exist_ok=True)
        # Create user's destination mount directory
        self.mount_dir.mkdir(parents=True, exist_ok=True)

        # Add pointer to /etc/auto.master.gpiupdate.d in /etc/auto.master
        auto_destdir = '+dir:{}'.format(self.__auto_dir)
        add_line_if_missing(self.__auto_file, auto_destdir)

        # Collect data for drive settings
        drive_list = list()
        for drv in self.drives:
            drive_settings = dict()
            drive_settings['dir'] = drv.dir
            drive_settings['login'] = drv.login
            drive_settings['password'] = drv.password
            drive_settings['path'] = drv.path.replace('\\', '/')

            drive_list.append(drive_settings)

        mount_settings = dict()
        mount_settings['drives'] = drive_list
        mount_text = self.template_mountpoints.render(**mount_settings)

        with open(self.user_config.resolve(), 'w') as f:
            f.truncate()
            f.write(mount_text)
            f.flush()

        autofs_settings = dict()
        autofs_settings['home_dir'] = self.home
        autofs_settings['mount_file'] = self.user_config.resolve()
        autofs_text = self.template_auto.render(**autofs_settings)

        with open(self.user_autofs.resolve(), 'w') as f:
            f.truncate()
            f.write(autofs_text)
            f.flush()

