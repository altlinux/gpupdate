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

from .config import GPConfig


def default_policy_path():
    '''
    Returns path pointing to Default Policy directory.
    '''
    local_policy_default = '/usr/share/local-policy/default'
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


def local_policy_cache():
    '''
    Returns path to directory where lies local policy settings cache
    transformed into GPT.
    '''
    lpcache = pathlib.Path.joinpath(cache_dir(), 'local-policy')

    if not lpcache.exists():
        lpcache.mkdir(parents=True, exist_ok=True)

    return lpcache

