#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2021 BaseALT Ltd. <org@basealt.ru>
# Copyright (C) 2019-2021 Igor Chudov <nir@nir.org.ru>
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

import pathlib
import os
from pathlib import Path
from urllib.parse import urlparse
from util.util import get_homedir

from .config import GPConfig
from .exceptions import NotUNCPathError


def get_custom_policy_dir():
    '''
    Returns path pointing to Custom Policy directory.
    '''
    return '/etc/local-policy'

def local_policy_path(default_template_name="default"):
    '''
    Returns path pointing to Local Policy template directory.
    '''
    local_policy_dir = '/usr/share/local-policy'

    config = GPConfig()
    local_policy_template = config.get_local_policy_template()
    local_policy_template_path = os.path.join(local_policy_dir, local_policy_template)
    local_policy_default = os.path.join(local_policy_dir, default_template_name)

    result_path = pathlib.Path(local_policy_default)
    if os.path.exists(local_policy_template):
        result_path = pathlib.Path(local_policy_template)
    elif os.path.exists(local_policy_template_path):
        result_path = pathlib.Path(local_policy_template_path)

    return pathlib.Path(result_path)

def cache_dir():
    '''
    Returns path pointing to gpupdate's cache directory
    '''
    cachedir = pathlib.Path('/var/cache/gpupdate')

    if not cachedir.exists():
        cachedir.mkdir(parents=True, exist_ok=True)

    return cachedir

def file_cache_dir():
    '''
    Returns path pointing to gpupdate's cache directory
    '''
    cachedir = pathlib.Path('/var/cache/gpupdate_file_cache')
    if not cachedir.exists():
        cachedir.mkdir(parents=True, exist_ok=True)

    return cachedir

def file_cache_path_home(username) -> str:
    '''
    Returns the path pointing to the gpupdate cache directory in the /home directory.
    '''
    cachedir = f'{get_homedir(username)}/.cache/gpupdate'

    return cachedir

def local_policy_cache():
    '''
    Returns path to directory where lies local policy settings cache
    transformed into GPT.
    '''
    lpcache = pathlib.Path.joinpath(cache_dir(), 'local-policy')

    if not lpcache.exists():
        lpcache.mkdir(parents=True, exist_ok=True)

    return lpcache

def get_dconf_config_path(uid = None):
    if uid:
        return f'/etc/dconf/db/policy{uid}.d/policy{uid}.ini'
    else:
        return '/etc/dconf/db/policy.d/policy.ini'

def get_desktop_files_directory():
    return '/usr/share/applications'

class UNCPath:
    def __init__(self, path):
        self.path = path
        self.type = None
        if self.path.startswith(r'smb://'):
            self.type = 'uri'
        if self.path.startswith(r'\\') or self.path.startswith(r'//'):
            self.type = 'unc'
        if not self.type:
            raise NotUNCPathError(path)

    def get_uri(self):
        path = self.path
        if self.type == 'unc':
            path = self.path.replace('\\', '/')
            path = path.replace('//', 'smb://')
        else:
            pass

        return path

    def get_unc(self):
        path = self.path
        if self.type == 'uri':
            path = self.path.replace('//', '\\\\')
            path = path.replace('smb:\\\\', '\\\\')
            path = path.replace('/', '\\')
        else:
            pass

        return path

    def get_domain(self):
        schema_struct = urlparse(self.get_uri())
        return schema_struct.netloc

    def get_path(self):
        schema_struct = urlparse(self.get_uri())
        return schema_struct.path

    def __str__(self):
        return self.get_uri()

