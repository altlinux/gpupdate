import logging

from .registry import registry

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

class samba_preg(object):
    def __init__(self, preg_obj):
        self.hive_key = '{}\\{}'.format(preg_obj.keyname, preg_obj.valuename)
        self.type = preg_obj.type
        self.data = preg_obj.data

class samba_hkcu_preg(object):
    def __init__(self, sid, preg_obj):
        self.sid = sid
        self.hive_key = '{}\\{}'.format(preg_obj.keyname, preg_obj.valuename)
        self.type = preg_obj.type
        self.data = preg_obj.data

class ad_shortcut(object):
    def __init__(self, sid, sc):
        self.sid = sid
        self.path = sc.dest
        self.shortcut = sc.to_json()

class info_entry(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class sqlite_registry(registry):
    __registry_path = 'sqlite:////var/cache/samba'

    def __init__(self, db_name):
        self.db_name = db_name
        self.db_path = os.path.join(self.__registry_path, '{}.sqlite'.format(self.db_name))
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

        self.__metadata.create_all(self.db_cnt)
        Session = sessionmaker(bind=self.db_cnt)
        self.db_session = Session()
        try:
            mapper(info_entry, self.__info)
            mapper(samba_preg, self.__hklm)
            mapper(samba_hkcu_preg, self.__hkcu)
            mapper(ad_shortcut, self.__shortcuts)
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
            self.db_session.query(info_entry).filter(info_entry.name == row.name).update(update_obj)
            self.db_session.commit()

    def _hklm_upsert(self, row):
        try:
            self._add(row)
        except:
            update_obj = dict({'type': row.type, 'data': row.data })
            self.db_session.query(samba_preg).filter(samba_preg.hive_key == row.hive_key).update(update_obj)
            self.db_session.commit()

    def _hkcu_upsert(self, row):
        try:
            self._add(row)
        except:
            update_obj = dict({'type': row.type, 'data': row.data })
            self.db_session.query(samba_preg).filter(samba_hkcu_preg.sid == row.sid).filter(samba_hkcu_preg.hive_key == row.hive_key).update(update_obj)
            self.db_session.commit()

    def _shortcut_upsert(self, row):
        try:
            self._add(row)
        except:
            update_obj = dict({ 'shortcut': row.shortcut })
            self.db_session.query(ad_shortcut).filter(ad_shortcut.sid == row.sid).filter(ad_shortcut.path == row.path).update(update_obj)
            self.db_session.commit()

    def set_info(self, name, value):
        ientry = info_entry(name, value)
        logging.debug('Setting info {}:{}'.format(name, value))
        self._info_upsert(ientry)

    def add_hklm_entry(self, preg_entry):
        '''
        Write PReg entry to HKEY_LOCAL_MACHINE
        '''
        pentry = samba_preg(preg_entry)
        self._hklm_upsert(pentry)

    def add_hkcu_entry(self, preg_entry, sid):
        '''
        Write PReg entry to HKEY_CURRENT_USER
        '''
        hkcu_pentry = samba_hkcu_preg(sid, preg_entry)
        logging.debug('Adding HKCU entry for {}'.format(sid))
        self._hkcu_upsert(hkcu_pentry)

    def add_shortcut(self, sid, sc_obj):
        '''
        Store shortcut information in the database
        '''
        sc_entry = ad_shortcut(sid, sc_obj)
        logging.debug('Saving info about {} link for {}'.format(sc_entry.path, sid))
        self._shortcut_upsert(sc_entry)

    def get_shortcuts(self, sid):
        res = self.db_session.query(ad_shortcut).filter(ad_shortcut.sid == sid).all()
        return res

    def get_hkcu_entry(self, sid, hive_key):
        res = self.db_session.query(samba_preg).filter(samba_hkcu_preg.sid == sid).filter(samba_hkcu_preg.hive_key == hive_key).first()
        # Try to get the value from machine SID as a default if no option is set.
        if not res:
            machine_sid = self.get_info('machine_sid')
            res = self.db_session.query(samba_preg).filter(samba_hkcu_preg.sid == machine_sid).filter(samba_hkcu_preg.hive_key == hive_key).first()
        return res

    def filter_hkcu_entries(self, sid, startswith):
        res = self.db_session.query(samba_hkcu_preg).filter(samba_hkcu_preg.sid == sid).filter(samba_hkcu_preg.hive_key.like(startswith))
        machine_sid = self.get_info('machine_sid')
        machine_res = self.db_session.query(samba_hkcu_preg).filter(samba_hkcu_preg.sid == machine_sid).filter(samba_hkcu_preg.hive_key.like(startswith))
        return res + machine_res

    def get_info(self, name):
        res = self.db_session.query(info_entry).filter(info_entry.name == name).first()
        return res.value

    def get_hklm_entry(self, hive_key):
        res = self.db_session.query(samba_preg).filter(samba_preg.hive_key == hive_key).first()
        return res

    def filter_hklm_entries(self, startswith):
        res = self.db_session.query(samba_preg).filter(samba_preg.hive_key.like(startswith))
        return res

    def wipe_user(self, sid):
        self.wipe_hkcu(sid)
        self.wipe_shortcuts(sid)

    def wipe_shortcuts(self, sid):
        self.db_session.query(ad_shortcut).filter(ad_shortcut.sid == sid).delete()
        self.db_session.commit()

    def wipe_hkcu(self, sid):
        self.db_session.query(samba_hkcu_preg).filter(samba_hkcu_preg.sid == sid).delete()
        self.db_session.commit()

    def wipe_hklm(self):
        self.db_session.query(samba_preg).delete()
        self.db_session.commit()

