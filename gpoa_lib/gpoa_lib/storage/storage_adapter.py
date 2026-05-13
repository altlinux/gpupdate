#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

from .dconf_registry import (
    PregDconf,
    convert_string_dconf,
    filter_dict_keys,
    find_preg_type,
    flatten_dictionary,
)
from ..util.logging import log
from ..util.paths import get_dconf_config_path


_TRUE_STRINGS = {
    "True", "true", "TRUE",
    "yes", "Yes",
    "enabled", "enable", "Enabled", "Enable",
    "1",
}


class StorageAdapter:
    '''
    Drop-in replacement for Dconf_registry for external usage.
    Reads from a specified dconf database instead of the global GPT registry.
    Implements Category A interface used by most appliers.
    '''

    def __init__(self, db_name=None, uid=None, prefix=None, keys=None, data=None):
        if data is not None:
            self._data = dict(data)
        elif db_name is not None:
            self._data = self._load_from_db(db_name, uid)
        else:
            self._data = {}

        if prefix:
            self._data = self._filter_prefix(prefix)
        elif keys:
            self._data = self._filter_keys(keys)

    @classmethod
    def from_dconf_db(cls, db_name, uid=None):
        return cls(db_name=db_name, uid=uid)

    @classmethod
    def from_dict(cls, data):
        return cls(data=data)

    @classmethod
    def from_dconf_db_prefix(cls, db_name, prefix, uid=None):
        return cls(db_name=db_name, uid=uid, prefix=prefix)

    @classmethod
    def from_dconf_db_keys(cls, db_name, keys, uid=None):
        return cls(db_name=db_name, uid=uid, keys=keys)

    def _load_from_db(self, db_name, uid=None):
        try:
            import gi
            gi.require_version("Gvdb", "1.0")
            gi.require_version("GLib", "2.0")
            from gi.repository import GLib, Gvdb

            if uid:
                path_bin = get_dconf_config_path(uid)
            else:
                dconf_dir = '/etc/dconf/db/'
                path_bin = dconf_dir + db_name

            output_dict = {}
            if GLib.file_get_contents(path_bin)[0]:
                bytes1 = GLib.Bytes.new(GLib.file_get_contents(path_bin)[1])
                table = Gvdb.Table.new_from_bytes(bytes1, True)

                name_list = Gvdb.Table.get_names(table)
                for name in name_list:
                    value = Gvdb.Table.get_value(table, name)
                    if value is None:
                        continue
                    list_path = name.split('/')
                    if value.is_of_type(GLib.VariantType('s')):
                        part = output_dict.setdefault('/'.join(list_path[1:-1]), {})
                        part[list_path[-1]] = value.get_string()
                    elif value.is_of_type(GLib.VariantType('i')):
                        part = output_dict.setdefault('/'.join(list_path[1:-1]), {})
                        part[list_path[-1]] = value.get_int32()
            return output_dict
        except Exception as exc:
            logdata = {'exc': str(exc), 'db_name': db_name}
            log('D217', logdata)
            return {}

    def _filter_prefix(self, prefix):
        flat = flatten_dictionary(self._data)
        filtered = filter_dict_keys(prefix, flat)
        result = {}
        for key, value in filtered.items():
            parts = key.rsplit('/', 1)
            if len(parts) == 2:
                section = result.setdefault(parts[0], {})
                section[parts[1]] = value
            else:
                result[key] = value
        return result

    def _filter_keys(self, keys):
        flat = flatten_dictionary(self._data)
        result = {}
        for key in keys:
            norm_key = key.lstrip('/')
            if norm_key in flat:
                parts = norm_key.rsplit('/', 1)
                if len(parts) == 2:
                    section = result.setdefault(parts[0], {})
                    section[parts[1]] = flat[norm_key]
                else:
                    result[norm_key] = flat[norm_key]
        return result

    def filter_hklm_entries(self, startswith):
        pregs = []
        flat = flatten_dictionary(self._data)
        if startswith and startswith[-1] == '%':
            startswith = startswith[:-1]
        filtered = filter_dict_keys(startswith, flat)
        for keyname, value in filtered.items():
            if isinstance(value, dict):
                for valuename, data in value.items():
                    pregs.append(PregDconf(
                        keyname, convert_string_dconf(valuename),
                        find_preg_type(data), data))
            elif isinstance(value, list):
                for data in value:
                    pregs.append(PregDconf(
                        keyname, data, find_preg_type(data), data))
            else:
                pregs.append(PregDconf(
                    '/'.join(keyname.split('/')[:-1]),
                    convert_string_dconf(keyname.split('/')[-1]),
                    find_preg_type(value), value))
        return pregs

    def filter_hkcu_entries(self, startswith):
        return self.filter_hklm_entries(startswith)

    def filter_entries(self, startswith):
        return self.filter_hklm_entries(startswith)

    def get_hklm_entry(self, hive_key):
        return self.get_entry(hive_key)

    def get_hkcu_entry(self, hive_key):
        return self.get_entry(hive_key)

    def get_entry(self, path, preg=True):
        flat = flatten_dictionary(self._data)
        norm = path.replace('\\', '/').lstrip('/')
        if norm in flat:
            data = flat[norm]
            keys = norm.rsplit('/', 1)
            key = keys[0] if len(keys) == 2 else ''
            valuename = keys[-1]
            if preg:
                return PregDconf(
                    key, convert_string_dconf(valuename),
                    find_preg_type(data), data)
            return data
        keys = path.replace('\\', '/').split('/')
        key = '/'.join(keys[:-1]) if keys[0] else '/'.join(keys[:-1])[1:]
        section = self._data.get(key)
        if isinstance(section, dict) and keys[-1] in section:
            data = section[keys[-1]]
            if preg:
                return PregDconf(
                    key, convert_string_dconf(keys[-1]),
                    find_preg_type(data), data)
            return data
        return None

    def get_key_value(self, key):
        result = self.get_entry(key, preg=False)
        return result

    def check_enable_key(self, key):
        data = self.get_entry(key, preg=False)
        if data is not None:
            if isinstance(data, str):
                return data in _TRUE_STRINGS
            elif isinstance(data, int):
                return bool(data)
        return False
