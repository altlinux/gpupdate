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
from .exceptions import NotUNCPathError

def local_policy_custom_templates_dir():
    '''
    Returns path pointing to custom templates directory.
    '''
    return '/etc/local-policy'

def local_policy_system_templates_dir():
    '''
    Returns path pointing to system templates directory.
    '''
    return '/usr/share/local-policy'

def _local_policy_templates_entries(directory):
    '''
    Get list of directories representing "Local Policy Default" templates.
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

def local_policy_templates():
    '''
    Get the list of local policy templates deployed on this system.
    Please note that is case overlapping names the names in
    /etc/local-policy must override names in /usr/share/local-policy
    '''
    system_templates_dir = local_policy_system_templates_dir()
    custom_templates_dir = local_policy_custom_templates_dir()

    system_templates = _local_policy_templates_entries(system_templates_dir)
    custom_templates = _local_policy_templates_entries(custom_templates_dir)

    general_listing = list()
    general_listing.extend(system_templates)
    general_listing.extend(custom_templates)

    return general_listing

def local_policy_template_path(default_template_name="default"):
    '''
    Returns path pointing to Local Policy template directory.
    '''
    system_templates_dir = local_policy_system_templates_dir()
    custom_templates_dir = local_policy_custom_templates_dir()

    config = GPConfig()
    template_name = config.get_local_policy_template()
    system_template_path = os.path.join(system_templates_dir, template_name)
    custom_template_path = os.path.join(custom_templates_dir, template_name)
    default_template_path = os.path.join(system_templates_dir, default_template_name)

    result_path = pathlib.Path(default_template_path)
    if os.path.exists(template_name):
        result_path = pathlib.Path(template_name)
    elif os.path.exists(custom_template_path):
        result_path = pathlib.Path(custom_template_path)
    elif os.path.exists(system_template_path):
        result_path = pathlib.Path(system_template_path)

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

def local_policy_path():
    '''
    Returns path to directory where GPT local admin policy.
    '''
    return '/etc/gpupdate/local_policy'

def local_policy_default_cache():
    '''
    Returns path to directory where lies local policy default settings cache
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

