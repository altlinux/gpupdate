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
import subprocess

from .logging import log


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


def set_privileges(username, uid, gid, groups, home):
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
    os.environ['HOME'] = home

    logdata = dict()
    logdata['uid'] = uid
    logdata['gid'] = gid
    logdata['username'] = username
    log('D37', logdata)


def with_privileges(username, func):
    '''
    Run supplied function with privileges for specified username.
    '''
    if not os.getuid() == 0:
        raise Exception('Not enough permissions to drop privileges')

    user_pw = pwd.getpwnam(username)
    user_uid = user_pw.pw_uid
    user_gid = user_pw.pw_gid
    user_groups = os.getgrouplist(username, user_gid)
    user_home = user_pw.pw_dir

    pid = os.fork()
    if pid > 0:
        log('D54', {'pid': pid})
        waitpid, status = os.waitpid(pid, 0)

        if status != 0:
            raise Exception('Error in forked process with droped privileges')

        return

    # Drop privileges
    set_privileges(username, user_uid, user_gid, user_groups, user_home)

    # Run the D-Bus session daemon in order D-Bus calls to work
    proc = subprocess.Popen(
        'dbus-launch',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    for var in proc.stdout:
        sp = var.decode('utf-8').split('=', 1)
        os.environ[sp[0]] = sp[1][:-1]

    # We need to return child error code to parent
    result = 0
    try:
        func()
    except Exception as exc:
        result = 127;

    sys.exit(result)

