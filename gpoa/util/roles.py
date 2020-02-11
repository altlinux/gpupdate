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


import logging
import pathlib
import subprocess

from .logging import slogm


def get_roles(role_dir):
    '''
    Return list of directories in /etc/role named after role plus '.d'
    '''
    directories = list()
    try:
        for item in role_dir.iterdir():
            if item.is_dir():
                role = str(item.name).rpartition('.')
                if role[2] == 'd':
                    directories.append(role[0])
    except FileNotFoundError as exc:
        logging.warning(slogm('No role directory present (skipping): {}'.format(exc)))

    return directories


def read_groups(role_file_path):
    '''
    Read list of whitespace-separated groups from file
    '''
    groups = list()

    with open(role_file_path, 'r') as role_file:
        lines = role_file.readlines()
        for line in lines:
            linegroups = line.strip().split(' ')
            print(linegroups)
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
    cmd = ['/usr/sbin/roleadd',
        '--set',
        role_name
    ]
    try:
        print(privilege_list)
        cmd.extend(privilege_list)
        subprocess.check_call(cmd)
    except Exception as exc:
        logging.error(slogm('Error creating role \'{}\': {}'.format(role_name, exc)))

def fill_roles():
    '''
    Create the necessary roles
    '''
    alterator_roles_dir = pathlib.Path('/etc/alterator/auth')
    nss_roles_dir = pathlib.Path('/etc/role.d')

    roles = get_roles(nss_roles_dir)

    # Compatibility with 'alterator-auth' module
    admin_groups = read_groups(pathlib.Path(alterator_roles_dir, 'admin-groups'))
    user_groups = read_groups(pathlib.Path(alterator_roles_dir, 'user-groups'))

    create_role('localadmins', admin_groups)
    create_role('users', user_groups)

    for rolename in roles:
        role_path = pathlib.Path(nss_roles_dir, '{}.d'.format(rolename))

        rolegroups = get_rolegroups(role_path)

        create_role(rolename, rolegroups)

