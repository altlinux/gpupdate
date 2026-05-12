#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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
import subprocess

from .logging import log
from .samba import smbopts
from .util import get_machine_name
from .ipa import ipaopts


def machine_kinit(cache_name=None, backend_type=None):
    '''
    Perform kinit with machine credentials
    '''
    if backend_type == 'freeipa':
        keytab_path = '/etc/samba/samba.keytab'
        opts = ipaopts()
        host = "cifs/" + opts.get_machine_name()
        realm = opts.get_realm()
        with_realm = '{}@{}'.format(host, realm)
        kinit_cmd = ['kinit', '-kt', keytab_path, with_realm]
    else:
        opts = smbopts()
        host = get_machine_name()
        realm = opts.get_realm()
        with_realm = '{}@{}'.format(host, realm)
        kinit_cmd = ['kinit', '-k', with_realm]

    if cache_name:
        os.environ['KRB5CCNAME'] = 'FILE:{}'.format(cache_name)
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

    if cache_name or 'KRB5CCNAME' in os.environ:
        proc = subprocess.Popen(kdestroy_cmd, stderr=subprocess.DEVNULL)
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
        result = True
        logdata = {'output': output}
        log('D17', logdata)
    except Exception as exc:
        logdata = {'krb-exc': exc}
        log('E14', logdata)

    return result
