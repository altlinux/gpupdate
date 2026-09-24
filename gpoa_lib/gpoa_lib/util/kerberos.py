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
import time

from .logging import log
from .samba import smbopts
from .util import get_machine_name

_owned_caches = set()


def forget_machine_cache(cache_name):
    _owned_caches.discard((os.getpid(), cache_name))


def destroy_owned_machine_caches():
    """Clean up only caches explicitly acquired by this process."""
    for pid, cache_name in tuple(_owned_caches):
        if pid == os.getpid():
            try:
                machine_kdestroy(cache_name)
            except Exception as exc:
                log('E14', {'krb-exc': exc})


def _wait_process(proc, timeout, cancelled=None):
    deadline = time.monotonic() + timeout
    try:
        while True:
            if cancelled and cancelled():
                raise InterruptedError('Kerberos operation cancelled')
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(proc.args, timeout)
            try:
                return proc.wait(timeout=min(remaining, 0.2) if cancelled else timeout)
            except subprocess.TimeoutExpired:
                if not cancelled:
                    raise
    except BaseException:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        proc.wait()
        raise


def machine_kinit(cache_name=None, backend_type=None, cancelled=None):
    '''
    Perform kinit with machine credentials
    '''
    if backend_type == 'freeipa':
        from .ipa import ipaopts
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
        _owned_caches.add((os.getpid(), cache_name))
        os.environ['KRB5CCNAME'] = 'FILE:{}'.format(cache_name)
        kinit_cmd.extend(['-c', cache_name])

    with subprocess.Popen(kinit_cmd) as proc:
        _wait_process(proc, 15, cancelled)

    result = False

    if 0 == proc.returncode:
        result = True

    if result:
        if cancelled and cancelled():
            raise InterruptedError('Kerberos operation cancelled')
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
        with subprocess.Popen(kdestroy_cmd, stderr=subprocess.DEVNULL) as proc:
            _wait_process(proc, 10)

    if cache_name and os.path.exists(cache_name):
        os.unlink(cache_name)
    elif 'KRB5CCNAME' in os.environ:
        path = os.environ['KRB5CCNAME'][5:]
        if os.path.exists(path):
            os.unlink(path)
    if cache_name:
        forget_machine_cache(cache_name)


def check_krb_ticket():
    '''
    Check if Kerberos 5 ticket present
    '''
    result = False
    try:
        subprocess.check_call(['klist', '-s'], timeout=10)
        output = subprocess.check_output(['klist'], stderr=subprocess.STDOUT, timeout=10).decode()
        result = True
        logdata = {'output': output}
        log('D17', logdata)
    except Exception as exc:
        logdata = {'krb-exc': exc}
        log('E14', logdata)

    return result
