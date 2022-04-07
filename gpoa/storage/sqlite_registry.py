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

from sqlalchemy import (
    create_engine,
    Table,
    Column,
    Integer,
    String,
    MetaData,
    UniqueConstraint
)
from sqlalchemy.orm import (
    mapper,
    sessionmaker
)

from util.logging import log
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
    , script_entry
)

class sqlite_registry(registry):
    def __init__(self, db_name, registry_cache_dir=None):
        self.db_name = db_name
        cdir = registry_cache_dir
        if cdir == None:
            cdir = cache_dir()
        self.db_path = os.path.join('sqlite:///{}/{}.sqlite'.format(cdir, self.db_name))
        self.db_cnt = create_engine(self.db_path, echo=False)
        self.__metadata = MetaData(self.db_cnt)
        self.__info = Table(
            'info',
            self.__metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(65536), unique=True),
            Column('value', String(65536))
        )
        self.__hklm = Table(
              'HKLM'
            , self.__metadata
            , Column('id', Integer, primary_key=True)
            , Column('hive_key', String(65536, collation='NOCASE'),
                unique=True)
            , Column('keyname', String(collation='NOCASE'))
            , Column('valuename', String(collation='NOCASE'))
            , Column('policy_name', String)
            , Column('type', Integer)
            , Column('data', String)
        )
        self.__hkcu = Table(
              'HKCU'
            , self.__metadata
            , Column('id', Integer, primary_key=True)
            , Column('sid', String)
            , Column('hive_key', String(65536, collation='NOCASE'))
            , Column('keyname', String(collation='NOCASE'))
            , Column('valuename', String(collation='NOCASE'))
            , Column('policy_name', String)
            , Column('type', Integer)
            , Column('data', String)
            , UniqueConstraint('sid', 'hive_key')
        )
        self.__shortcuts = Table(
              'Shortcuts'
            , self.__metadata
            , Column('id', Integer, primary_key=True)
            , Column('sid', String)
            , Column('path', String)
            , Column('policy_name', String)
            , Column('shortcut', String)
            , UniqueConstraint('sid', 'path')
        )
        self.__printers = Table(
              'Printers'
            , self.__metadata
            , Column('id', Integer, primary_key=True)
            , Column('sid', String)
            , Column('name', String)
            , Column('policy_name', String)
            , Column('printer', String)
            , UniqueConstraint('sid', 'name')
        )
        self.__drives = Table(
              'Drives'
            , self.__metadata
            , Column('id', Integer, primary_key=True)
            , Column('sid', String)
            , Column('login', String)
            , Column('password', String)
            , Column('dir', String)
            , Column('policy_name', String)
            , Column('path', String)
            , UniqueConstraint('sid', 'dir')
        )
        self.__folders = Table(
              'Folders'
            , self.__metadata
            , Column('id', Integer, primary_key=True)
            , Column('sid', String)
            , Column('path', String)
            , Column('policy_name', String)
            , Column('action', String)
            , Column('delete_folder', String)
            , Column('delete_sub_folders', String)
            , Column('delete_files', String)
            , UniqueConstraint('sid', 'path')
        )
        self.__envvars = Table(
              'Envvars'
            , self.__metadata
            , Column('id', Integer, primary_key=True)
            , Column('sid', String)
            , Column('name', String)
            , Column('policy_name', String)
            , Column('action', String)
            , Column('value', String)
            , UniqueConstraint('sid', 'name')
        )
        self.__scripts = Table(
              'Scripts'
            , self.__metadata
            , Column('id', Integer, primary_key=True)
            , Column('sid', String)
            , Column('policy_name', String)
            , Column('queue', String)
            , Column('action', String)
            , Column('path', String)
            , Column('arg', String)
            , UniqueConstraint('sid', 'path', 'arg')
        )
        self.__metadata.create_all(self.db_cnt)
        Session = sessionmaker(bind=self.db_cnt)
        self.db_session = Session()
        try:
            mapper(info_entry, self.__info)
            mapper(samba_preg, self.__hklm)
            mapper(samba_hkcu_preg, self.__hkcu)
            mapper(ad_shortcut, self.__shortcuts)
            mapper(printer_entry, self.__printers)
            mapper(drive_entry, self.__drives)
            mapper(folder_entry, self.__folders)
            mapper(envvar_entry, self.__envvars)
            mapper(script_entry, self.__scripts)
        except:
            pass
            #logging.error('Error creating mapper')

    def _add(self, row):
        try:
            self.db_session.add(row)
            self.db_session.commit()
        except Exception as exc:
            self.db_session.rollback()
            raise exc

    def _info_upsert(self, row):
        try:
            self._add(row)
        except:
            (self
                .db_session.query(info_entry)
                .filter(info_entry.name == row.name)
                .update(row.update_fields()))
            self.db_session.commit()

    def _hklm_upsert(self, row):
        try:
            self._add(row)
        except:
            (self
                .db_session
                .query(samba_preg)
                .filter(samba_preg.hive_key == row.hive_key)
                .update(row.update_fields()))
            self.db_session.commit()

    def _hkcu_upsert(self, row):
        try:
            self._add(row)
        except Exception as exc:
            (self
                .db_session
                .query(samba_hkcu_preg)
                .filter(samba_hkcu_preg.sid == row.sid)
                .filter(samba_hkcu_preg.hive_key == row.hive_key)
                .update(row.update_fields()))
            self.db_session.commit()

    def _shortcut_upsert(self, row):
        try:
            self._add(row)
        except:
            (self
                .db_session
                .query(ad_shortcut)
                .filter(ad_shortcut.sid == row.sid)
                .filter(ad_shortcut.path == row.path)
                .update(row.update_fields()))
            self.db_session.commit()

    def _printer_upsert(self, row):
        try:
            self._add(row)
        except:
            (self
                .db_session
                .query(printer_entry)
                .filter(printer_entry.sid == row.sid)
                .filter(printer_entry.name == row.name)
                .update(row.update_fields()))
            self.db_session.commit()

    def _drive_upsert(self, row):
        try:
            self._add(row)
        except:
            (self
                .db_session
                .query(drive_entry)
                .filter(drive_entry.sid == row.sid)
                .filter(drive_entry.dir == row.dir)
                .update(row.update_fields()))
            self.db_session.commit()

    def set_info(self, name, value):
        ientry = info_entry(name, value)
        logdata = dict()
        logdata['varname'] = name
        logdata['value'] = value
        log('D19', logdata)
        self._info_upsert(ientry)

    def _delete_hklm_keyname(self, keyname):
        '''
        Delete PReg hive_key from HKEY_LOCAL_MACHINE
        '''
        logdata = dict({'keyname': keyname})
        try:
            (self
                .db_session
                .query(samba_preg)
                .filter(samba_preg.keyname == keyname)
                .delete(synchronize_session=False))
            self.db_session.commit()
            log('D65', logdata)
        except Exception as exc:
            log('D63', logdata)

    def add_hklm_entry(self, preg_entry, policy_name):
        '''
        Write PReg entry to HKEY_LOCAL_MACHINE
        '''
        pentry = samba_preg(preg_entry, policy_name)
        if not pentry.valuename.startswith('**'):
            self._hklm_upsert(pentry)
        else:
            logdata = dict({'key': pentry.hive_key})
            if pentry.valuename.lower() == '**delvals.':
                self._delete_hklm_keyname(pentry.keyname)
            else:
                log('D27', logdata)

    def _delete_hkcu_keyname(self, keyname, sid):
        '''
        Delete PReg hive_key from HKEY_CURRENT_USER
        '''
        logdata = dict({'sid': sid, 'keyname': keyname})
        try:
            (self
                .db_session
                .query(samba_hkcu_preg)
                .filter(samba_hkcu_preg.sid == sid)
                .filter(samba_hkcu_preg.keyname == keyname)
                .delete(synchronize_session=False))
            self.db_session.commit()
            log('D66', logdata)
        except:
            log('D64', logdata)

    def add_hkcu_entry(self, preg_entry, sid, policy_name):
        '''
        Write PReg entry to HKEY_CURRENT_USER
        '''
        hkcu_pentry = samba_hkcu_preg(sid, preg_entry, policy_name)
        logdata = dict({'sid': sid, 'policy': policy_name, 'key': hkcu_pentry.hive_key})
        if not hkcu_pentry.valuename.startswith('**'):
            log('D26', logdata)
            self._hkcu_upsert(hkcu_pentry)
        else:
            if hkcu_pentry.valuename.lower() == '**delvals.':
                self._delete_hkcu_keyname(hkcu_pentry.keyname, sid)
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
    def add_script(self, sid, scrobj, policy_name):
        scr_entry = script_entry(sid, scrobj, policy_name)
        logdata = dict()
        logdata['script path'] = scrobj.path
        logdata['sid'] = sid
        log('D152', logdata)
        try:
            self._add(scr_entry)
        except Exception as exc:
            (self
                ._filter_sid_obj(script_entry, sid)
                .filter(script_entry.path == scr_entry.path)
                .update(scr_entry.update_fields()))
            self.db_session.commit()


    def _filter_sid_obj(self, row_object, sid):
        res = (self
            .db_session
            .query(row_object)
            .filter(row_object.sid == sid))
        return res

    def _filter_sid_list(self, row_object, sid):
        res = (self
            .db_session
            .query(row_object)
            .filter(row_object.sid == sid)
            .order_by(row_object.id)
            .all())
        return res

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

    def get_scripts(self, sid):
        return self._filter_sid_list(script_entry, sid)


    def get_hkcu_entry(self, sid, hive_key):
        res = (self
            .db_session
            .query(samba_hkcu_preg)
            .filter(samba_hkcu_preg.sid == sid)
            .filter(samba_hkcu_preg.hive_key == hive_key)
            .first())
        # Try to get the value from machine SID as a default if no option is set.
        if not res:
            machine_sid = self.get_info('machine_sid')
            res = self.db_session.query(samba_hkcu_preg).filter(samba_hkcu_preg.sid == machine_sid).filter(samba_hkcu_preg.hive_key == hive_key).first()
        return res

    def filter_hkcu_entries(self, sid, startswith):
        res = (self
            .db_session
            .query(samba_hkcu_preg)
            .filter(samba_hkcu_preg.sid == sid)
            .filter(samba_hkcu_preg.hive_key.like(startswith)))
        return res

    def get_info(self, name):
        res = (self
            .db_session
            .query(info_entry)
            .filter(info_entry.name == name)
            .first())
        return res.value

    def get_hklm_entry(self, hive_key):
        res = (self
            .db_session
            .query(samba_preg)
            .filter(samba_preg.hive_key == hive_key)
            .first())
        return res

    def filter_hklm_entries(self, startswith):
        res = (self
            .db_session
            .query(samba_preg)
            .filter(samba_preg.hive_key.like(startswith)))
        return res

    def wipe_user(self, sid):
        self._wipe_sid(samba_hkcu_preg, sid)
        self._wipe_sid(ad_shortcut, sid)
        self._wipe_sid(printer_entry, sid)
        self._wipe_sid(drive_entry, sid)
        self._wipe_sid(script_entry, sid)

    def _wipe_sid(self, row_object, sid):
        (self
            .db_session
            .query(row_object)
            .filter(row_object.sid == sid)
            .delete())
        self.db_session.commit()

    def wipe_hklm(self):
        self.db_session.query(samba_preg).delete()
        self.db_session.commit()

