#
# Copyright (C) 2019-2020 BaseALT Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import json
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
        args.update(dict({'timestamp': now, 'message': str(self.message)}))
        args.update(self.kwargs)

        kwa = encoder().encode(args)

        result = '{}:{}'.format(now.rpartition('.')[0], self.message)

        return result

