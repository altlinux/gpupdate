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
import re
from pathlib import Path
from .samba import smbopts
import ast


def get_machine_name():
    '''
    Get localhost name looking like DC0$
    '''
    loadparm = smbopts()
    result = loadparm.get_machine_name()

    return result


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

def homedir_exists(username):
    '''
    Check that home directory exists for specified user.

    :param username: string representing user name to work with
    :return: True in case home directory exists and False otherwise
    '''
    hd = Path(get_homedir(username))

    if hd.exists() and hd.is_dir():
        return True

    return False

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

def runcmd(command_name):
    '''
    Run application.
    '''
    try:
        with subprocess.Popen(command_name, stdout=subprocess.PIPE) as proc:
            value = proc.stdout.read().decode('utf-8')
            proc.wait()
            rc = proc.returncode
            return (rc, value)
    except Exception as exc:
        print(str(exc))

def get_backends():
    '''
    Get the list of backends supported by GPOA
    '''
    return ['local', 'samba']

def get_default_policy_name():
    '''
    Determine the preferred Local Policy template name according to
    ALT distribution type
    '''
    localpolicy = 'workstation'
    dcpolicy = 'ad-domain-controller'

    try:
        if smbopts().get_server_role() == 'active directory domain controller':
            return dcpolicy
    except:
        pass

    try:
        release = '/etc/altlinux-release'
        if os.path.isfile(release):
            f = open(release)
            s = f.readline()
            if re.search('server', s, re.I):
                localpolicy = 'server'
    except:
        pass

    return localpolicy

def get_policy_entries(directory):
    '''
    Get list of directories representing "Local Policy" templates.
    '''
    filtered_entries = list()
    if os.path.isdir(directory):
        entries = [os.path.join(directory, entry) for entry in os.listdir(directory)]

        for entry in entries:
            if os.path.isdir(os.path.join(entry)):
                if not os.path.islink(os.path.join(entry)):
                    if not entry.rpartition('/')[2] == 'default':
                        filtered_entries.append(entry)

    return filtered_entries

def get_policy_variants():
    '''
    Get the list of local policy variants deployed on this system.
    Please note that is case overlapping names the names in
    /etc/local-policy must override names in /usr/share/local-policy
    '''
    policy_dir = '/usr/share/local-policy'
    etc_policy_dir = '/etc/local-policy'

    system_policies = get_policy_entries(policy_dir)
    user_policies = get_policy_entries(etc_policy_dir)

    general_listing = list()
    general_listing.extend(system_policies)
    general_listing.extend(user_policies)

    return general_listing

def string_to_literal_eval(string):
    try:
        literaleval = ast.literal_eval(string)
    except:
        literaleval = string
    return literaleval

def touch_file(filename):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()

