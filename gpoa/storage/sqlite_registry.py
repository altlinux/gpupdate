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

        self.__metadata.create_all(self.db_cnt)
        Session = sessionmaker(bind=self.db_cnt)
        self.db_session = Session()
        try:
            mapper(samba_preg, self.__hklm)
        except:
            logging.error('Error creating mapper')

    def _upsert(self, row):
        try:
            self.db_session.add(row)
            self.db_session.commit()
        except:
            logging.error('Row update failed, updating row')
            self.db_session.rollback()
            self.db_session.query(samba_preg).filter(samba_preg.hive_key == row.hive_key).update({'type': row.type, 'data': row.data })
            self.db_session.commit()

    def add_hklm_entry(self, preg_entry):
        pentry = samba_preg(preg_entry)
        self._upsert(pentry)

    def add_hkcu_entry(self, preg_entry, sid):
        pass

    def get_entry(self, hive_key):
        res = self.db_session.query(samba_preg).filter(samba_preg.hive_key == hive_key).first()
        return res

    def filter_hklm_entries(self, startswith):
        res = self.db_session.query(samba_preg).filter(samba_preg.hive_key.like(startswith))
        return res

