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
import subprocess

from .util import get_machine_name
from .logging import slogm


def machine_kinit():
    '''
    Perform kinit with machine credentials
    '''
    host = get_machine_name()
    subprocess.call(['kinit', '-k', host])
    return check_krb_ticket()


def check_krb_ticket():
    '''
    Check if Kerberos 5 ticket present
    '''
    result = False
    try:
        subprocess.check_call(['klist', '-s'])
        output = subprocess.check_output('klist', stderr=subprocess.STDOUT).decode()
        logging.info(output)
        result = True
    except:
        logging.error(slogm('Kerberos ticket check unsuccessful'))

    logging.debug(slogm('Ticket check succeed'))

    return result
