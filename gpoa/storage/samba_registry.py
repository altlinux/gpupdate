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

import os

from util.logging import log
import samba.reg_api
from util.paths import cache_dir
from .registry import registry
from .record_types import (
      samba_preg
    , samba_hkcu_preg
    , ad_shortcut
    , info_entry
    , printer_entry
    , drive_entry
    , folder_entry
    , envvar_entry
)

class SambaRegistry(registry):
    def __init__(self):
        pass

    def set_info(self, name, value):
        ientry = info_entry(name, value)
        logdata = dict()
        logdata['varname'] = name
        logdata['value'] = value
        log('D19', logdata)
        self._info_upsert(ientry)

    def add_hklm_entry(self, preg_entry, policy_name):
        '''
        Write PReg entry to HKEY_LOCAL_MACHINE
        '''
        pentry = samba_preg(preg_entry, policy_name)
        if not pentry.hive_key.rpartition('\\')[2].startswith('**'):
            #samba.smbregapi.upsert_hklm(preg_entry.keyname, preg_entry.valuename, preg_entry.data, preg_entry.type)
            samba.reg_api.upsert_key(preg_entry.keyname, preg_entry.valuename, preg_entry.data)
        else:
            logdata = dict({'key': pentry.hive_key})
            log('D27', logdata)

    def add_hkcu_entry(self, preg_entry, sid, policy_name):
        '''
        Write PReg entry to HKEY_CURRENT_USER
        '''
        hkcu_pentry = samba_hkcu_preg(sid, preg_entry, policy_name)
        logdata = dict({'sid': sid, 'policy': policy_name, 'key': hkcu_pentry.hive_key})
        if not hkcu_pentry.hive_key.rpartition('\\')[2].startswith('**'):
            log('D26', logdata)
            samba.reg_api.upsert_key('HKU\\{}\\{}'.format(sid, hkcu_pentry.keyname), hkcu_pentry.valuename, hkcu_pentry.data)
        else:
            log('D51', logdata)

    def add_shortcut(self, sid, sc_obj, policy_name):
        '''
        Store shortcut information in the database
        '''
        sc_entry = ad_shortcut(sid, sc_obj, policy_name)
        logdata = dict()
        logdata['link'] = sc_entry.path
        logdata['sid'] = sid
        log('D41', logdata)
        self._shortcut_upsert(sc_entry)

    def add_printer(self, sid, pobj, policy_name):
        '''
        Store printer configuration in the database
        '''
        prn_entry = printer_entry(sid, pobj, policy_name)
        logdata = dict()
        logdata['printer'] = prn_entry.name
        logdata['sid'] = sid
        log('D40', logdata)
        self._printer_upsert(prn_entry)

    def add_drive(self, sid, dobj, policy_name):
        drv_entry = drive_entry(sid, dobj, policy_name)
        logdata = dict()
        logdata['uri'] = drv_entry.path
        logdata['sid'] = sid
        log('D39', logdata)
        self._drive_upsert(drv_entry)

    def add_folder(self, sid, fobj, policy_name):
        fld_entry = folder_entry(sid, fobj, policy_name)
        logdata = dict()
        logdata['folder'] = fld_entry.path
        logdata['sid'] = sid
        log('D42', logdata)
        try:
            self._add(fld_entry)
        except Exception as exc:
            (self
                ._filter_sid_obj(folder_entry, sid)
                .filter(folder_entry.path == fld_entry.path)
                .update(fld_entry.update_fields()))
            self.db_session.commit()

    def add_envvar(self, sid, evobj, policy_name):
        ev_entry = envvar_entry(sid, evobj, policy_name)
        logdata = dict()
        logdata['envvar'] = ev_entry.name
        logdata['sid'] = sid
        log('D53', logdata)
        try:
            self._add(ev_entry)
        except Exception as exc:
            (self
                ._filter_sid_obj(envvar_entry, sid)
                .filter(envvar_entry.name == ev_entry.name)
                .update(ev_entry.update_fields()))
            self.db_session.commit()

    def get_shortcuts(self, sid):
        return self._filter_sid_list(ad_shortcut, sid)

    def get_printers(self, sid):
        return self._filter_sid_list(printer_entry, sid)

    def get_drives(self, sid):
        return self._filter_sid_list(drive_entry, sid)

    def get_folders(self, sid):
        return self._filter_sid_list(folder_entry, sid)

    def get_envvars(self, sid):
        return self._filter_sid_list(envvar_entry, sid)

    def get_hkcu_entry(self, sid, hive_key):
        split_query_key = pentry.hive_key.rpartition('\\')
        key = samba.reg_api.get_key('HKU\\{}\\{}'.format(sid, split_query_key[0]), split_query_key[2])
        return key

    def filter_hkcu_entries(self, sid, startswith):
        keys = samba.reg_api.filter_branch('HKU\\{}\\{}'.format(sid, startswith))
        full_keys = list()
        # Glue the key name with the branch name
        for key in keys:
            full_keys.append('HKU\\{}\\{}\\{}'.format(sid, startswith, key))

        return full_keys

    def get_info(self, name):
        res = (self
            .db_session
            .query(info_entry)
            .filter(info_entry.name == name)
            .first())
        return res.value

    def get_hklm_entry(self, hive_key):
        split_query_key = pentry.hive_key.rpartition('\\')
        key = samba.reg_api.get_key('HKLM\\{}'.format(split_query_key[0]), split_query_key[2])
        return key

    def filter_hklm_entries(self, startswith):
        keys = samba.reg_api.filter_branch(startswith)
        full_keys = list()
        # Glue the key name with the branch name
        for key in keys:
            full_keys.append('{}\\{}'.format(startswith, key))

        return full_keys

    def wipe_user(self, sid):
        samba.reg_api.delete_branch('HKU\\{}'.format(sid))

    def wipe_hklm(self):
        samba.reg_api.delete_branch('HKLM\\Software')

