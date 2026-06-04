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

import os

from .dconf_registry import Dconf_registry, create_dconf_file_locks, get_keys_dconf_locks
from ..util.ini_writer import write_ini_sections
from ..util.logging import log
from ..util.paths import get_dconf_db_path, get_dconf_db_file


class StorageWriter:
    '''
    Write policy data to an arbitrary dconf database.

    Parameters
    ----------
    db_name : str
        Database name under ``/etc/dconf/db/``.  For example ``'local'``
        writes to ``/etc/dconf/db/local.d/local.ini``.
    uid : int, optional
        User UID for per-user databases (appended to db_name).
    append : bool
        If ``True``, append to the existing INI file instead of
        overwriting.  Default ``False``.

    Examples
    --------
    ::

        from gpoa_lib import StorageWriter

        writer = StorageWriter('local')
        writer.write({'Software/BaseALT/Policies/Control': {'sshd-gssapi-auth': '1'}})
        writer.compile()

        writer.write_keys({'Software/BaseALT/Policies/Control/sshd-gssapi-auth': '1'})
        writer.compile()
    '''

    def __init__(self, db_name, uid=None, append=False):
        self.db_name = db_name
        self.uid = uid
        self._append = append

    def _get_ini_path(self):
        return get_dconf_db_file(self.db_name)

    def _get_ini_dir(self):
        return get_dconf_db_path(self.db_name)

    def write(self, data):
        ini_path = self._get_ini_path()
        ini_dir = self._get_ini_dir()

        os.makedirs(ini_dir, exist_ok=True)

        mode = 'a' if self._append else 'w'
        with open(ini_path, mode) as f:
            write_ini_sections(f, data)

        logdata = {'path': ini_path, 'db_name': self.db_name}
        log('D209', logdata)
        create_dconf_file_locks(ini_path, data)

    def write_keys(self, keys_dict):
        '''
        Write a flat dict ``{full_path: value}`` to the database INI file.

        The path is split into section and value name at the last ``/``.

        Parameters
        ----------
        keys_dict : dict
            Flat dict mapping full registry paths to values.
            Example: ``{'Software/BaseALT/Policies/Control/sshd': '1'}``
        '''
        grouped = {}
        for full_path, value in keys_dict.items():
            norm = full_path.replace('\\', '/').lstrip('/')
            parts = norm.rsplit('/', 1)
            if len(parts) == 2:
                section = grouped.setdefault(parts[0], {})
                section[parts[1]] = value
            else:
                section = grouped.setdefault(norm, {})
                section['_value'] = value
        self.write(grouped)

    def delete_keys(self, keys):
        '''
        Remove specific keys from the database INI file.

        Rewrites the INI file excluding the listed keys.

        Parameters
        ----------
        keys : list[str]
            Full registry paths to remove.
        '''
        ini_path = self._get_ini_path()
        if not os.path.exists(ini_path):
            return

        normalized = set()
        for k in keys:
            normalized.add(k.replace('\\', '/').lstrip('/'))

        with open(ini_path, 'r') as f:
            content = f.read()

        import re
        from ..util.gpoa_ini_parsing import GpoaConfigObj
        config = GpoaConfigObj(content.split('\n'))

        for section_key in list(config.keys()):
            section_norm = section_key.replace('\\', '/').lstrip('/')
            if isinstance(config[section_key], dict):
                for val_key in list(config[section_key].keys()):
                    full = f'{section_norm}/{val_key}'
                    if full in normalized:
                        del config[section_key][val_key]
                if not config[section_key]:
                    del config[section_key]

        os.makedirs(self._get_ini_dir(), exist_ok=True)
        with open(ini_path, 'w') as f:
            for section, section_data in config.items():
                if not section:
                    continue
                f.write(f'[{section}]\n')
                if isinstance(section_data, dict):
                    for key, value in section_data.items():
                        if not key:
                            continue
                        if isinstance(value, int):
                            f.write(f'{key} = {value}\n')
                        else:
                            f.write(f'{key} = "{value}"\n')
                f.write('\n')

        logdata = {'path': ini_path, 'deleted': len(normalized)}
        log('D209', logdata)

    def compile(self):
        '''
        Compile the database from its INI sources.

        Calls ``dconf compile`` for this database.
        '''
        Dconf_registry.dconf_update(uid=self.uid, db_name=self.db_name)
