from .cache import cache

class mapped_id(object):
    def __init__(self, str_id, value):
        self.str_id = str_id
        self.value = value

class sqlite_cache(cache):
    __cache_dir = '/var/cache/samba'
    def __init__(self, cache_name):
        self.cache_name = cache_name
        self.db_cnt = create_engine(os.path.join(self.__cache_dir, self.cache_name), echo=False)
        self.__metadata = MetaData(self.db_cnt)
        self.cache_table = Table(
            self.cache_name,
            self.__metadata,
            Column('id', Integer, primary_key=True),
            Column('str_id', String(65536)),
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
        result = self.db_session.query(mapped_id).filter(mapped_id.str_id == obj_id)
        return result[0]

    def _upsert(self, obj):
        self.db_session.add(obj)
        self.db_session.commit()

