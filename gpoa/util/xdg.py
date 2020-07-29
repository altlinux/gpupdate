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


import os

from .util import get_homedir
from .logging import log

def xdg_get_desktop(username, homedir = None):
    if username:
        homedir = get_homedir(username)
    if not homedir:
        msgtext = message_with_code('E18')
        logdata = dict()
        logdata['username'] = username
        log('E18', logdata)
        raise Exception(msgtext)

    stream = os.popen('export HOME={}; xdg-user-dir DESKTOP'.format(homedir))
    output = stream.read()[:-1]
    return output

