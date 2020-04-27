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

import pathlib
import os


def default_policy_path():
    '''
    Returns path pointing to Default Policy directory.
    '''
    local_policy_default = '/usr/share/local-policy/default'
    etc_local_policy_default = '/etc/local-policy/active'

    result_path = pathlib.Path(local_policy_default)

    if os.path.exists(etc_local_policy_default):
        result_path = pathlib.Path(etc_local_policy_default)

    return pathlib.Path(result_path)


def cache_dir():
    '''
    Returns path pointing to gpupdate's cache directory
    '''
    cachedir = pathlib.Path('/var/cache/gpupdate')

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

def backend_module_dir():
    backend_dir = '/usr/lib/gpoa/backend'
    return pathlib.Path(backend_dir)

def frontend_module_dir():
    frontend_dir = '/usr/lib/gpoa/frontend'
    return pathlib.Path(frontend_dir)

def storage_module_dir():
    storage_dir = '/usr/lib/gpoa/storage'
    return pathlib.Path(storage_dir)

def pre_backend_plugin_dir():
    pre_backend_dir = '/usr/lib/gpoa/backend_pre'
    return pathlib.Path(pre_backend_dir)

def post_backend_plugin_dir():
    post_backend_dir = '/usr/lib/gpoa/backend_post'
    return pathlib.Path(post_backend_dir)

def pre_frontend_plugin_dir():
    pre_forntend_dir = '/usr/lib/gpoa/frontend_pre'
    return pathlib.Path(pre_frontend_dir)

def post_frontend_plugin_dir():
    post_frontend_dir = '/usr/lib/gpoa/frontend_post'
    return pathlib.Path(post_frontend_dir)

