from .cache import cache

import logging
import os

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

class mapped_id(object):
    def __init__(self, str_id, value):
        self.str_id = str_id
        self.value = value

class sqlite_cache(cache):
    __cache_dir = 'sqlite:////var/cache/samba'

    def __init__(self, cache_name):
        self.cache_name = cache_name
        self.storage_uri = os.path.join(self.__cache_dir, '{}.sqlite'.format(self.cache_name))
        logging.debug('Initializing cache {}'.format(self.storage_uri))
        self.db_cnt = create_engine(self.storage_uri, echo=False)
        self.__metadata = MetaData(self.db_cnt)
        self.cache_table = Table(
            self.cache_name,
            self.__metadata,
            Column('id', Integer, primary_key=True),
            Column('str_id', String(65536), unique=True),
            Column('value', String)
        )

        self.__metadata.create_all(self.db_cnt)
        Session = sessionmaker(bind=self.db_cnt)
        self.db_session = Session()
        try:
            mapper(mapped_id, self.cache_table)
        except:
            logging.error('Error creating mapper')

    def store(self, str_id, value):
        obj = mapped_id(str_id, value)
        self._upsert(obj)

    def get(self, obj_id):
        result = self.db_session.query(mapped_id).filter(mapped_id.str_id == obj_id).first()
        return result

    def get_default(self, obj_id, default_value):
        result = self.get(obj_id)
        if not result:
            logging.debug('No value cached for {}'.format(obj_id))
            self.store(obj_id, default_value)
            return None
        return result

    def _upsert(self, obj):
        try:
            self.db_session.add(obj)
            self.db_session.commit()
        except:
            self.db_session.rollback()
            logging.error('Error inserting value into cache, will update the value')
            self.db_session.query(mapped_id).filter(mapped_id.str_id == obj.str_id).update({ 'value': obj.value })
            self.db_session.commit()

