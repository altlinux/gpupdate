from abc import ABC

class cache(ABC):
    def __init__(self):
        pass

    @classmethod
    def store(self, str_id, value):
        '''
        '''
        pass

    @classmethod
    def get(self, obj_id):
        '''
        '''
        pass

    @classmethod
    def get_default(self, obj_id, default_value):
        '''
        '''
        pass

