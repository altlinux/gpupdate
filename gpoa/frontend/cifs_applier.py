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

from .applier_frontend import applier_frontend
from gpt.drives import json2drive

def storage_get_drives(storage, sid):
    drives = storage.get_drives(sid)
    drive_list = list()

    for drv_obj in drives:
        drv = json2drive(drv_obj)
        drive_list.append(drive_list)

    return drive_list

class cifs_applier(applier_frontend):
    def __init__(self, storage):
        pass

    def apply(self):
        pass

class cifs_applier_user(applier_frontend):
    __auto_file = '/etc/auto.master'
    __drive_entry_template = '/mnt/{}\t/etc/auto.smb\t-t 120'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self.drives = storage_get_drives(self.storage, self.sid)

    def user_context_apply(self):
        '''
        Nothing to implement.
        '''
        pass


    def admin_context_apply(self):
        with open(self.__auto_file, 'w') as auf:
            for drv in self.drives:
                for line in auf:
                    if line.startswith('/mnt/{}'.format(drv.dir))
                        break
                else:
                    auf.write(self.__drive_entry_template.format(drv.dir))

