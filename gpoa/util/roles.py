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

import pathlib
import os
import subprocess

def get_roles():
    '''
    Return list of directories in /etc/role named after role plus '.d'
    '''
    default_path = pathib.Path('/etc/role')

    directories = list()
    for item in default_path.iterdir():
        if item.is_dir():
            role = str(item.name).rpartition('.')
            if role[2] == 'd':
                directories.append(role[0])

    return directories


def read_groups(role_file_path):
    '''
    Read list of whitespace-separated groups from file
    '''
    groups = list()

    with open(role_file_path, 'r') as role_file:
        line = role_file.readline()
        while line:
            linegroups = line.split(' ')
            groups.extend(linegroups)

    return set(groups)


def get_rolegroups(roledir):
    '''
    Get the list of groups which must be included into role.
    '''
    roledir_path = pathlib.Path(roledir)

    group_files = list()
    for item in roledir_path.iterdir():
        if item.is_file():
            group_files.append(item)

    groups = list()
    for item in group_files:
        groups.extend(read_groups(item))

    return set(groups)

def create_role(role_name, privilege_list):
    '''
    Create or update role
    '''
    subprocess.check_call(['/usr/sbin/roleadd',
        '--set',
        '--skip-missed',
        role_name].extend(privilege_list))

def fill_roles():
    '''
    Create the necessary roles
    '''
    alterator_roles_dir = pathlib.Path('/etc/alterator/auth')
    roles = get_roles()

    # Compatibility with 'alterator-auth' module
    admin_groups = get_rolegroups(pathlib.Path(alterator_roles_dir, 'admin-groups'))
    user_groups = get_rolegroups(pathlib.Path(alterator_roles_dir, 'user-groups'))

    create_role(localadmins, admin_groups)
    create_role(users, user_groups)

    for rolename in roles:
        role_path = pathlib.Path('/etc/role.d', '{}.d'.format(rolename))

        rolegroups = get_rolegroups(role_path)

        create_role(rolename, rolegroups)

