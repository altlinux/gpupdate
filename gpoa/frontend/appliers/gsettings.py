#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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

import configparser
import os
from gi.repository import Gio, GLib

from util.logging import log

class system_gsetting:
    def __init__(self, schema, path, value, lock, helper_function=None):
        self.schema = schema
        self.path = path
        self.value = value
        self.lock = lock
        self.helper_function = helper_function

    def apply(self, settings, config, locks):
        try:
            config.add_section(self.schema)
        except configparser.DuplicateSectionError:
            pass

        value = self.value
        if self.helper_function:
            value = self.helper_function(self.schema, self.path, value)
        result = glib_value(self.schema, self.path, value, settings)
        config.set(self.schema, self.path, str(result))

        if self.lock:
            lock_path = dconf_path(settings, self.path)
            locks.append(lock_path)

class system_gsettings:
    __path_local_dir = '/etc/dconf/db/local.d'
    __path_locks = '/etc/dconf/db/policy.d/locks/policy'
    __path_profile = '/etc/dconf/profile/user'
    __profile_data = 'user-db:user\nsystem-db:policy\nsystem-db:local\n'

    def __init__(self, override_file_path):
        self.gsettings = list()
        self.locks = list()
        self.override_file_path = override_file_path

    def append(self, schema, path, data, lock, helper):
        if check_existing_gsettings(schema, path):
            self.gsettings.append(system_gsetting(schema, path, data, lock, helper))
        else:
            logdata = dict()
            logdata['schema'] = schema
            logdata['path'] = path
            logdata['data'] = data
            logdata['lock'] = lock
            log('D150', logdata)

    def apply(self):
        config = configparser.ConfigParser()

        for gsetting in self.gsettings:
            logdata = dict()
            logdata['gsetting.schema'] = gsetting.schema
            logdata['gsetting.path'] = gsetting.path
            logdata['gsetting.value'] = gsetting.value
            logdata['gsetting.lock'] = gsetting.lock
            settings = Gio.Settings(schema=gsetting.schema)
            log('D89', logdata)
            gsetting.apply(settings, config, self.locks)

        with open(self.override_file_path, 'w') as f:
            config.write(f)

        os.makedirs(self.__path_local_dir, mode=0o755, exist_ok=True)
        os.makedirs(os.path.dirname(self.__path_locks), mode=0o755, exist_ok=True)
        os.makedirs(os.path.dirname(self.__path_profile), mode=0o755, exist_ok=True)
        try:
            os.remove(self.__path_locks)
        except OSError as error:
            pass

        file_locks = open(self.__path_locks,'w')
        for lock in self.locks:
            file_locks.write(lock +'\n')
        file_locks.close()

        profile = open(self.__path_profile ,'w')
        profile.write(self.__profile_data)
        profile.close()

def glib_map(value, glib_type):
    result_value = value

    if glib_type == 'i' or glib_type == 'b' or glib_type == 'q':
        result_value = GLib.Variant(glib_type, int(value))
    else:
        result_value = GLib.Variant(glib_type, value)

    return result_value

def dconf_path(settings, path):
    return settings.get_property("path") + path

def glib_value(schema, path, value, settings):
    # Get the key to modify
    key = settings.get_value(path)
    # Query the data type for the key
    glib_value_type = key.get_type_string()
    # Build the new value with the determined type
    return glib_map(value, glib_value_type)

def check_existing_gsettings (schema, path):
    source = Gio.SettingsSchemaSource.get_default()
    sourceSchema = (source.lookup(schema, False))
    if bool(sourceSchema) and sourceSchema.has_key(path):
        return True
    else:
        return False

class user_gsettings:
    def __init__(self):
        self.gsettings = list()

    def append(self, schema, path, value, helper=None):
        if check_existing_gsettings(schema, path):
            self.gsettings.append(user_gsetting(schema, path, value, helper))
        else:
            logdata = dict()
            logdata['schema'] = schema
            logdata['path'] = path
            logdata['data'] = value
            log('D151', logdata)

    def apply(self):
        for gsetting in self.gsettings:
            logdata = dict()
            logdata['gsetting.schema'] = gsetting.schema
            logdata['gsetting.path'] = gsetting.path
            logdata['gsetting.value'] = gsetting.value
            log('D85', logdata)
            gsetting.apply()


class user_gsetting:
    def __init__(self, schema, path, value, helper_function=None):
        self.schema = schema
        self.path = path
        self.value = value
        self.helper_function = helper_function

    def apply(self):
        # Access the current schema
        settings = Gio.Settings(schema=self.schema)
        # Update result with helper function
        value = self.value
        if self.helper_function:
            value = self.helper_function(self.schema, self.path, value)
        # Get typed value by schema
        result = glib_value(self.schema, self.path, value, settings)
        # Set the value
        settings.set_value(self.path, result)
        settings.sync()
