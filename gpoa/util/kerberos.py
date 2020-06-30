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
import logging
import subprocess

from .util import get_machine_name
from .logging import slogm


def machine_kinit(cache_name=None):
    '''
    Perform kinit with machine credentials
    '''
    host = get_machine_name()
    kinit_cmd = ['kinit', '-k', host]
    if cache_name:
        kinit_cmd.extend(['-c', cache_name])
    proc = subprocess.Popen(kinit_cmd)
    proc.wait()

    result = False

    if 0 == proc.returncode:
        result = True

    if result:
        result = check_krb_ticket()

    return result


def machine_kdestroy(cache_name=None):
    '''
    Perform kdestroy for machine credentials
    '''
    host = get_machine_name()
    kdestroy_cmd = ['kdestroy']
    if cache_name:
        kdestroy_cmd.extend(['-c', cache_name])

    proc = subprocess.Popen(kdestroy_cmd)
    proc.wait()

    if cache_name and os.path.exists(cache_name):
        os.unlink(cache_name)
    elif 'KRB5CCNAME' in os.environ:
        path = os.environ['KRB5CCNAME'][5:]
        if os.path.exists(path):
            os.unlink(path)


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
