#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2021 BaseALT Ltd.
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

import json
import locale
import os
import pwd
import signal
import subprocess
import sys

from .dbus import dbus_session
from .logging import log
from .util import get_user_info


def set_privileges(username, uid, gid, groups, home):
    '''
    Set current process privileges
    '''
    defaultlocale = locale.getlocale()
    os.environ.clear()
    os.environ['HOME'] = home
    os.environ['USER'] = username
    os.environ['USERNAME'] = username
    if defaultlocale[0] and defaultlocale[1]:
        os.environ["LANG"] = '.'.join(defaultlocale)

    try:
        os.setgid(gid)
    except Exception as exc:
        raise Exception('Error setgid() for drop privileges: {}'.format(str(exc)))

    try:
        os.setgroups(groups)
    except Exception as exc:
        raise Exception('Error setgroups() for drop privileges: {}'.format(str(exc)))

    try:
        os.setuid(uid)
    except Exception as exc:
        raise Exception('Error setuid() for drop privileges: {}'.format(str(exc)))

    os.chdir(home)

    logdata = {'uid': uid, 'gid': gid, 'username': username}
    log('D37', logdata)


def _read_child_result(pid, rfd):
    import select
    import signal
    status = None

    def read_exact(size):
        nonlocal status
        chunks = []
        while size:
            readable, _, _ = select.select([rfd], [], [], 0.2)
            if readable:
                chunk = os.read(rfd, min(size, 65536))
                if not chunk:
                    raise RuntimeError('Incomplete forked process result')
                chunks.append(chunk)
                size -= len(chunk)
            else:
                if status is None:
                    exited, value = os.waitpid(pid, os.WNOHANG)
                    if exited:
                        status = value
                if status is not None:
                    raise RuntimeError('Forked process exited without a complete result')
        return b''.join(chunks)

    try:
        size = int.from_bytes(read_exact(8), 'big')
        if size > 64 * 1024 * 1024:
            raise RuntimeError('Forked process result exceeds 64 MiB')
        data = read_exact(size)
    except BaseException:
        if status is None:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        raise
    finally:
        os.close(rfd)
        if status is None:
            _, status = os.waitpid(pid, 0)
    if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
        raise RuntimeError('Error in forked process ({})'.format(status))
    return json.loads(data.decode('utf-8')) if data else None


def _write_child_result(wfd, result):
    payload = json.dumps(result).encode('utf-8')
    if len(payload) > 64 * 1024 * 1024:
        raise ValueError('Forked process result exceeds 64 MiB')
    data = memoryview(len(payload).to_bytes(8, 'big') + payload)
    while data:
        written = os.write(wfd, data)
        if not written:
            raise OSError('Unable to write child result')
        data = data[written:]


def with_privileges(username, func):
    '''
    Run supplied function with privileges for specified username and return JSON result of func().
    '''
    if os.getuid() != 0:
        raise Exception('Not enough permissions to drop privileges')

    # Resolve user information with retry
    max_retries = 3
    for attempt in range(max_retries):
        try:
            user_pw = get_user_info(username)
            break
        except KeyError:
            if attempt == max_retries - 1:
                raise
            import time
            time.sleep(0.5)  # Wait before retry

    user_uid = user_pw.pw_uid
    user_gid = user_pw.pw_gid
    user_groups = os.getgrouplist(username, user_gid)
    user_home = user_pw.pw_dir

    if not os.path.isdir(user_home):
        raise Exception('User home directory not exists')

    # Create a pipe for inter-process communication
    rfd, wfd = os.pipe()

    try:
        pid = os.fork()
    except BaseException:
        os.close(rfd)
        os.close(wfd)
        raise
    if pid > 0:
        # --- Parent process ---
        os.close(wfd)
        log('D54', {'pid': pid})

        return _read_child_result(pid, rfd)

    # Never unwind a forked worker into the parent's caller or finalizers.
    exitcode = 1
    try:
        os.close(rfd)
        exitcode = _run_privileged_child(
            username, user_uid, user_gid, user_groups, user_home, func, wfd)
    except BaseException as exc:
        log('E33', {'msg': str(exc)})
    finally:
        try:
            os.close(wfd)
        finally:
            os._exit(exitcode)


def _run_privileged_child(username, user_uid, user_gid, user_groups, user_home, func, wfd):
    result = None
    exitcode = 0
    dbus_pid = -1
    dconf_pid = -1
    try:
        # Drop privileges
        set_privileges(username, user_uid, user_gid, user_groups, user_home)

        # Start dbus-launch to get session bus
        with subprocess.Popen(
            ['dbus-launch'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        ) as proc:
            for var in proc.stdout:
                sp = var.decode('utf-8').split('=', 1)
                os.environ[sp[0]] = sp[1].strip()

        # Save DBus session PID
        dbus_pid = int(os.environ['DBUS_SESSION_BUS_PID'])

        # Execute target function and expect JSON-serializable result
        result = func()

        # Try to get dconf-service PID
        try:
            session = dbus_session()
            dconf_pid = session.get_connection_pid("ca.desrt.dconf")
        except Exception as exc:
            log('D307', {'exc': str(exc)})

    except Exception as exc:
        log('E33', {'msg': str(exc)})
        exitcode = 1
    finally:
        # Log dbus/dconf info
        log('D56', {'dbus_pid': dbus_pid, 'dconf_pid': dconf_pid})

        # Cleanup processes
        for pid, signum in ((dbus_pid, signal.SIGHUP),
                            (dconf_pid, signal.SIGTERM), (dbus_pid, signal.SIGTERM)):
            if pid > 0:
                try:
                    os.kill(pid, signum)
                except ProcessLookupError:
                    pass
                except OSError as exc:
                    log('D307', {'exc': str(exc)})
                    exitcode = 1

    # Serialize result to JSON and send to parent
    try:
        _write_child_result(wfd, result)
    except Exception as exc:
        log('D308', {'exc': str(exc)})
        exitcode = 1
    return exitcode
