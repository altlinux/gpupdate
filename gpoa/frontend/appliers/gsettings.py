#
# Copyright (C) 2019-2020 Igor Chudov
# Copyright (C) 2019-2020 Evgeny Sinelnikov
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

import configparser
import os
import logging
from gi.repository import Gio, GLib

class system_gsetting:
    def __init__(self, schema, path, value):
        self.schema = schema
        self.path = path
        self.value = value

    def apply(self):
        pass
        #source = Gio.SettingsSchemaSource.get_default()
        #schema = source.lookup(self.schema, True)
        #key = schema.get_key(self.path)
        #gvformat = key.get_value_type()
        #val = GLib.Variant(gvformat.dup_string(), self.value)
        #schema.set_value(self.path, val)

        #variants = gso.get_property(self.path)
        #if (variants.has_key(self.path)):
        #    key = variants.get_key(self.path)
        #    print(key.get_range())

class user_gsetting:
    def __init__(self, schema, path, value):
        self.schema = schema
        self.path = path
        self.value = value

    def apply(self):
        source = Gio.SettingsSchemaSource.get_default()
        schema = source.lookup(self.schema, True)
        key = schema.get_key(self.path)
        gvformat = key.get_value_type()
        val = GLib.Variant(gvformat.dup_string(), self.value)
        schema.set_value(self.path, val)
        #gso = Gio.Settings.new(self.schema)
        #variants = gso.get_property(self.path)
        #if (variants.has_key(self.path)):
        #    key = variants.get_key(self.path)
        #    print(key.get_range())

