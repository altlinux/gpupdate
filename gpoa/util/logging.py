import json
import logging
import datetime

class encoder(json.JSONEncoder):
    def default(self, obj):
        result = super(encoder, self).default(obj)

        if isinstance(obj, set):
            result = tuple(obj)
        if isinstance(obj, unicode):
            result = obj.encode('unicode_escape').decode('ascii')

        return result

class slogm(object):
    '''
    Structured log message class
    '''
    def __init__(self, message, **kwargs):
        self.message = message
        self.kwargs = kwargs

    def __str__(self):
        now = str(datetime.datetime.now())
        args = dict()
        args.update(dict({ 'timestamp': now, 'message': str(self.message) }))
        args.update(self.kwargs)

        kwa = encoder().encode(args)

        result = '{}:{}'.format(now.rpartition('.')[0], self.message)

        return result

