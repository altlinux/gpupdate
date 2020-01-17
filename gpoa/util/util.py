#
# Copyright (C) 2019-2020 BaseALT Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


import socket
import os
import pwd


def get_machine_name():
    '''
    Get localhost name looking like DC0$
    '''
    return socket.gethostname().split('.', 1)[0].upper() + "$"


def is_machine_name(name):
    '''
    Check if supplied username is machine name in fact.
    '''
    return name == get_machine_name()


def traverse_dir(root_dir):
    '''
    Recursively fetch all files from directory and its subdirectories.
    '''
    filelist = []
    for root, dirs, files in os.walk(root_dir):
        for filename in files:
            filelist.append(os.path.join(root, filename))
    return filelist


def get_homedir(username):
    '''
    Query password database for user's home directory.
    '''
    return pwd.getpwnam(username).pw_dir


def mk_homedir_path(username, homedir_path):
    '''
    Create subdirectory in user's $HOME.
    '''
    homedir = get_homedir(username)
    uid = pwd.getpwnam(username).pw_uid
    gid = pwd.getpwnam(username).pw_gid

    elements = homedir_path.split('/')
    longer_path = homedir
    for elem in elements:
        os.makedirs(longer_path, exist_ok=True)
        os.chown(homedir, uid=uid, gid=gid)
        longer_path = os.path.join(longer_path, elem)

