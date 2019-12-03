import logging

from .registry import registry
from sqlalchemy import (
    create_engine,
    Table,
    Column,
    Integer,
    String,
    MetaData
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

class sqlite_registry(registry):
    __registry_path = 'sqlite:////var/cache/samba/registry.sqlite'

    def __init__(self, db_name):
        self.db_name = db_name
        self.db_cnt = create_engine(self.__registry_path, echo=False)
        self.__metadata = MetaData(self.db_cnt)
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
            Column('data', String)
        )

        self.__metadata.create_all(self.db_cnt)
        Session = sessionmaker(bind=self.db_cnt)
        self.db_session = Session()
        try:
            mapper(samba_preg, self.__hklm)
            mapper(samba_hkcu_preg, self.__hkcu)
        except:
            logging.error('Error creating mapper')

    def _hklm_upsert(self, row):
        try:
            self.db_session.add(row)
            self.db_session.commit()
        except:
            logging.error('Row update failed, updating row')
            self.db_session.rollback()
            self.db_session.query(samba_preg).filter(samba_preg.hive_key == row.hive_key).update({'type': row.type, 'data': row.data })
            self.db_session.commit()

    def _hkcu_upsert(self, row):
        try:
            self.db_session.add(row)
            self.db_session.commit()
        except:
            logging.error('Row update failed, updating row')
            self.db_session.rollback()
            self.db_session.query(samba_preg).filter(samba_hkcu_preg.sid == row.sid).filter(samba_hkcu_preg.hive_key == row.hive_key).update({'type': row.type, 'data': row.data })
            self.db_session.commit()

    def add_hklm_entry(self, preg_entry):
        pentry = samba_preg(preg_entry)
        self._hklm_upsert(pentry)

    def add_hkcu_entry(self, preg_entry, sid):
        hkcu_pentry = samba_hkcu_preg(sid, preg_entry)
        logging.debug('Adding HKCU entry for {}'.format(sid))
        self._hkcu_upsert(hkcu_pentry)

    def get_hkcu_entry(self, sid, hive_key):
        res = self.db_session.query(samba_preg).filter(samba_hkcu_preg.sid == sid).filter(samba_hkcu_preg.hive_key == hive_key).first()
        return res

    def filter_hkcu_entries(self, sid, startswith):
        res = self.db_session.query(samba_preg).filter(samba_hkcu_preg.sid == sid).filter(samba_hkcu_preg.hive_key.like(startswith))
        return res

    def get_hklm_entry(self, hive_key):
        res = self.db_session.query(samba_preg).filter(samba_preg.hive_key == hive_key).first()
        return res

    def filter_hklm_entries(self, startswith):
        res = self.db_session.query(samba_preg).filter(samba_preg.hive_key.like(startswith))
        return res

