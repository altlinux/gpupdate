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

import logging

from util.windows import smbcreds
from .samba_backend import samba_backend
from .nodomain_backend import nodomain_backend
from util.logging import slogm
from messages import message_with_code

def backend_factory(dc, username, is_machine, no_domain = False):
    '''
    Return one of backend objects. Please note that backends must
    store their configuration in a storage with administrator
    write permissions in order to prevent users from modifying
    policies enforced by domain administrators.
    '''
    back = None
    domain = None
    if not no_domain:
        sc = smbcreds(dc)
        domain = sc.get_domain()

    if domain:
        ldata = dict({'domain': domain})
        logging.debug(slogm(message_with_code('I4'), ldata))
        try:
            back = samba_backend(sc, username, domain, is_machine)
        except Exception as exc:
            logdata = dict({'error': str(exc)})
            logging.error(slogm(message_with_code('E7'), logdata))
    else:
        logging.debug(slogm(message_with_code('I5')))
        try:
            back = nodomain_backend()
        except Exception as exc:
            logdata = dict({'error': str(exc)})
            logging.error(slogm(message_with_code('E8'), logdata))

    return back

