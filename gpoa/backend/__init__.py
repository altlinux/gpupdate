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

import logging

from util.windows import smbcreds
from .samba_backend import samba_backend
from .nodomain_backend import nodomain_backend

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
        logging.debug('Initialize Samba backend for domain: {}'.format(domain))
        try:
            back = samba_backend(sc, username, domain, is_machine)
        except Exception as exc:
            logging.error('Unable to initialize Samba backend: {}'.format(exc))
    else:
        logging.debug('Initialize local backend with no domain')
        try:
            back = nodomain_backend()
        except Exception as exc:
            logging.error('Unable to initialize no-domain backend: {}'.format(exc))

    return back

