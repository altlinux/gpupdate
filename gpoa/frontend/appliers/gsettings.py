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

import configparser
import os
import logging
from gi.repository import Gio, GLib

from util.logging import slogm

class system_gsetting:
    __global_schema = '/usr/share/glib-2.0/schemas'

    def __init__(self, schema, path, value, override_priority='0'):
        self.schema = schema
        self.path = path
        self.value = value
        self.override_priority = override_priority
        self.filename = '{}_policy.gschema.override'.format(self.override_priority)
        self.file_path = os.path.join(self.__global_schema, self.filename)

    def apply(self):
        config = configparser.ConfigParser()
        try:
            config.read(self.file_path)
        except Exception as exc:
            logging.error(slogm(exc))
        config.add_section(self.schema)
        config.set(self.schema, self.path, self.value)

        with open(self.file_path, 'w') as f:
            config.write(f)

def glib_map(value, glib_type):
    result_value = value

    if glib_type == 'i':
        result_value = GLib.Variant(glib_type, int(value))
    else:
        result_value = GLib.Variant(glib_type, value)

    return result_value

class user_gsetting:
    def __init__(self, schema, path, value, helper_function=None):
        logging.debug('Creating GSettings element {} (in {}) with value {}'.format(path, schema, value))
        self.schema = schema
        self.path = path
        self.value = value
        self.helper_function = helper_function

    def apply(self):
        logging.debug('Setting GSettings key {} (in {}) to {}'.format(self.path, self.schema, self.value))
        if self.helper_function:
            self.helper_function(self.schema, self.path, self.value)
        # Access the current schema
        settings = Gio.Settings(self.schema)
        # Get the key to modify
        key = settings.get_value(self.path)
        # Query the data type for the key
        glib_value_type = key.get_type_string()
        # Build the new value with the determined type
        val = glib_map(self.value, glib_value_type)
        # Set the value
        settings.set_value(self.path, val)

        #gso = Gio.Settings.new(self.schema)
        #variants = gso.get_property(self.path)
        #if (variants.has_key(self.path)):
        #    key = variants.get_key(self.path)
        #    print(key.get_range())

