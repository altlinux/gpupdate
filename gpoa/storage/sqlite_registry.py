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

import logging
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

from util.logging import slogm
from util.paths import cache_dir
from .registry import registry
from .record_types import (
      samba_preg
    , samba_hkcu_preg
    , ad_shortcut
    , info_entry
    , printer_entry
)

class sqlite_registry(registry):
    def __init__(self, db_name):
        self.db_name = db_name
        self.db_path = os.path.join('sqlite:///{}/{}.sqlite'.format(cache_dir(), self.db_name))
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
            'HKLM',
            self.__metadata,
            Column('id', Integer, primary_key=True),
            Column('hive_key', String(65536), unique=True),
            Column('type', Integer),
            Column('data', String)
        )
        self.__hkcu = Table(
            'HKCU',
            self.__metadata,
            Column('id', Integer, primary_key=True),
            Column('sid', String),
            Column('hive_key', String(65536)),
            Column('type', Integer),
            Column('data', String),
            UniqueConstraint('sid', 'hive_key')
        )
        self.__shortcuts = Table(
            'Shortcuts',
            self.__metadata,
            Column('id', Integer, primary_key=True),
            Column('sid', String),
            Column('path', String),
            Column('shortcut', String),
            UniqueConstraint('sid', 'path')
        )
        self.__printers = Table(
            'Printers',
            self.__metadata,
            Column('id', Integer, primary_key=True),
            Column('sid', String),
            Column('name', String),
            Column('printer', String),
            UniqueConstraint('sid', 'name')
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
            update_obj = dict({ 'value': row.value })
            (self
                .db_session.query(info_entry)
                .filter(info_entry.name == row.name)
                .update(update_obj))
            self.db_session.commit()

    def _hklm_upsert(self, row):
        try:
            self._add(row)
        except:
            update_obj = dict({'type': row.type, 'data': row.data })
            (self
                .db_session
                .query(samba_preg)
                .filter(samba_preg.hive_key == row.hive_key)
                .update(update_obj))
            self.db_session.commit()

    def _hkcu_upsert(self, row):
        try:
            self._add(row)
        except:
            update_obj = dict({'type': row.type, 'data': row.data })
            (self
                .db_session
                .query(samba_preg)
                .filter(samba_hkcu_preg.sid == row.sid)
                .filter(samba_hkcu_preg.hive_key == row.hive_key)
                .update(update_obj))
            self.db_session.commit()

    def _shortcut_upsert(self, row):
        try:
            self._add(row)
        except:
            update_obj = dict({ 'shortcut': row.shortcut })
            (self
                .db_session
                .query(ad_shortcut)
                .filter(ad_shortcut.sid == row.sid)
                .filter(ad_shortcut.path == row.path)
                .update(update_obj))
            self.db_session.commit()

    def _printer_upsert(self, row):
        try:
            self._add(row)
        except:
            update_obj = dict({ 'printer': row.printer })
            (self
                .db_session
                .query(printer_entry)
                .filter(printer_entry.sid == row.sid)
                .filter(printer_entry.name == row.name)
                .update(update_obj))
            self.db_session.commit()

    def set_info(self, name, value):
        ientry = info_entry(name, value)
        logging.debug(slogm('Setting info {}:{}'.format(name, value)))
        self._info_upsert(ientry)

    def add_hklm_entry(self, preg_entry):
        '''
        Write PReg entry to HKEY_LOCAL_MACHINE
        '''
        pentry = samba_preg(preg_entry)
        if not pentry.hive_key.rpartition('\\')[2].startswith('**'):
            self._hklm_upsert(pentry)
        else:
            logging.warning(slogm('Skipping branch deletion key: {}'.format(pentry.hive_key)))

    def add_hkcu_entry(self, preg_entry, sid):
        '''
        Write PReg entry to HKEY_CURRENT_USER
        '''
        hkcu_pentry = samba_hkcu_preg(sid, preg_entry)
        if not hkcu_pentry.hive_key.rpartition('\\')[2].startswith('**'):
            logging.debug(slogm('Adding HKCU entry for {}'.format(sid)))
            self._hkcu_upsert(hkcu_pentry)
        else:
            logging.warning(slogm('Skipping branch deletion key: {}'.format(hkcu_pentry.hive_key)))

    def add_shortcut(self, sid, sc_obj):
        '''
        Store shortcut information in the database
        '''
        sc_entry = ad_shortcut(sid, sc_obj)
        logging.debug(slogm('Saving info about {} link for {}'.format(sc_entry.path, sid)))
        self._shortcut_upsert(sc_entry)

    def add_printer(self, sid, pobj):
        '''
        Store printer configuration in the database
        '''
        prn_entry = printer_entry(sid, pobj)
        logging.debug(slogm('Saving info about printer {} for {}'.format(prn_entry.name, sid)))
        self._printer_upsert(prn_entry)

    def get_shortcuts(self, sid):
        res = (self
            .db_session
            .query(ad_shortcut)
            .filter(ad_shortcut.sid == sid)
            .all())
        return res

    def get_printers(self, sid):
        res = (self
            .db_session
            .query(printer_entry)
            .filter(printer_entry.sid == sid)
            .all())
        return res

    def get_hkcu_entry(self, sid, hive_key):
        res = (self
            .db_session
            .query(samba_preg)
            .filter(samba_hkcu_preg.sid == sid)
            .filter(samba_hkcu_preg.hive_key == hive_key)
            .first())
        # Try to get the value from machine SID as a default if no option is set.
        if not res:
            machine_sid = self.get_info('machine_sid')
            res = self.db_session.query(samba_preg).filter(samba_hkcu_preg.sid == machine_sid).filter(samba_hkcu_preg.hive_key == hive_key).first()
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
        self.wipe_hkcu(sid)
        self.wipe_shortcuts(sid)
        self.wipe_printers(sid)

    def wipe_shortcuts(self, sid):
        (self
            .db_session
            .query(ad_shortcut)
            .filter(ad_shortcut.sid == sid)
            .delete())
        self.db_session.commit()

    def wipe_printers(self, sid):
        (self
            .db_session
            .query(printer_entry)
            .filter(printer_entry.sid == sid)
            .delete())
        self.db_session.commit()

    def wipe_hkcu(self, sid):
        (self
            .db_session
            .query(samba_hkcu_preg)
            .filter(samba_hkcu_preg.sid == sid)
            .delete())
        self.db_session.commit()

    def wipe_hklm(self):
        self.db_session.query(samba_preg).delete()
        self.db_session.commit()

