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

from .config import GPConfig
from .util import get_default_policy_name
from .util.exceptions import NotUNCPathError


def default_policy_path():
    '''
    Returns path pointing to Default Policy directory.
    '''
    local_policy_default = '/usr/share/local-policy/{}'.format(get_default_policy_name())
    config = GPConfig()

    result_path = pathlib.Path(local_policy_default)

    if os.path.exists(config.get_local_policy_template()):
        result_path = pathlib.Path(config.get_local_policy_template())

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

def local_policy_cache():
    '''
    Returns path to directory where lies local policy settings cache
    transformed into GPT.
    '''
    lpcache = pathlib.Path.joinpath(cache_dir(), 'local-policy')

    if not lpcache.exists():
        lpcache.mkdir(parents=True, exist_ok=True)

    return lpcache

class UNCPath:
    def __init__(self, path):
        self.path = path
        self.type = None
        if self.path.startswith(r'smb://'):
            self.type = 'uri'
        if self.path.startswith(r'\\'):
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

