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

import os
import pwd
import logging

from .logging import slogm


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
    uid = os.getuid()
    process_username = get_process_user()

    if process_username == username:
        return True

    return False


def set_privileges(username, uid, gid, groups=list()):
    '''
    Set current process privileges
    '''

    try:
        os.setegid(gid)
    except Exception as exc:
        print('setegid')
    try:
        os.seteuid(uid)
    except Exception as exc:
        print('seteuid')
    #try:
    #    os.setgroups(groups)
    #except Exception as exc:
    #    print('setgroups')

    logging.debug(
        slogm('Set process permissions to UID {} and GID {} for user {}'.format(
            uid, gid, username)))


def with_privileges(username, func):
    '''
    Run supplied function with privileges for specified username.
    '''
    current_uid = os.getuid()
    current_groups = os.getgrouplist('root', 0)

    if not current_uid == 0:
        raise Exception('Not enough permissions to drop privileges')

    user_uid = pwd.getpwnam(username).pw_uid
    user_gid = pwd.getpwnam(username).pw_gid
    user_groups = os.getgrouplist(username, user_gid)

    # Drop privileges
    set_privileges(username, user_uid, user_gid, user_groups)

    # We need to catch exception in order to be able to restore
    # privileges later in this function
    try:
        func()
    except Exception as exc:
        logging.debug(slogm(exc))

    # Restore privileges
    set_privileges('root', current_uid, 0, current_groups)

