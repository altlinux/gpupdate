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

def backend_factory(dc, username):
    '''
    Return one of backend objects. Please note that backends must
    store their configuration in a storage with administrator
    write permissions in order to prevent users from modifying
    policies enforced by domain administrators.
    '''
    sc = smbcreds(dc)
    domain = sc.get_domain()
    back = None

    try:
        back = samba_backend(sc, username, domain)
    except Exception as exc:
        logging.error('Unable to initialize Samba backend: {}'.format(exc))

    return back

