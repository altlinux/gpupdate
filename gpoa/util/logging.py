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

import datetime
import json
import logging

from gpoa.messages import message_with_code


class encoder(json.JSONEncoder):
    def default(self, obj):
        result = super(encoder, self)
        result = result.default(obj)

        if isinstance(obj, set):
            result = tuple(obj)
        if isinstance(obj, unicode):
            result = obj.encode('unicode_escape').decode('ascii')

        return result


class slogm(object):
    '''
    Structured log message class
    '''
    def __init__(self, message, kwargs={}):
        self.message = message
        self.kwargs = kwargs
        if not self.kwargs:
            self.kwargs = {}

    def __str__(self):
        now = str(datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds'))
        args = {}
        args.update(self.kwargs)
        result = '{}|{}|{}'.format(now, self.message, args)

        return result

def log(message_code, data=None):
    mtype = message_code[0]

    if 'I' == mtype:
        logging.info(slogm(message_with_code(message_code), data))
        return
    if 'W' == mtype:
        logging.warning(slogm(message_with_code(message_code), data))
        return
    if 'E' == mtype:
        logging.error(slogm(message_with_code(message_code), data))
        return
    if 'F' == mtype:
        logging.fatal(slogm(message_with_code(message_code), data))
        return
    if 'D' == mtype:
        logging.debug(slogm(message_with_code(message_code), data))
        return

    logging.error(slogm(message_with_code(message_code), data))

