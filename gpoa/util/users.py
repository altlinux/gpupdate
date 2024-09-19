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

import os
import pwd


def is_root():
    '''
    Check if current process has root permissions.
    '''
    if os.getuid() == 0:
        return True
    return False


def get_process_user():
    '''
    Get current process username.
    '''
    username = None

    uid = os.getuid()
    username = pwd.getpwuid(uid).pw_name

    return username


def username_match_uid(username):
    '''
    Check the passed username matches current process UID.
    '''
    process_username = get_process_user()

    if process_username == username:
        return True

    return False

