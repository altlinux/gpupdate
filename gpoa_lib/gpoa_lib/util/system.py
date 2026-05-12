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
    defaultlocale = locale.getdefaultlocale()
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

    pid = os.fork()
    if pid > 0:
        # --- Parent process ---
        os.close(wfd)
        log('D54', {'pid': pid})

        # Wait for child process
        waitpid, status = os.waitpid(pid, 0)
        code = os.WEXITSTATUS(status)
        if code != 0:
            raise Exception('Error in forked process ({})'.format(status))

        # Read data from pipe
        data = os.read(rfd, 10_000_000)
        os.close(rfd)

        if not data:
            return None

        # Deserialize JSON
        return json.loads(data.decode("utf-8"))

    # --- Child process ---
    os.close(rfd)

    result = None
    exitcode = 0
    dbus_pid = -1
    dconf_pid = -1
    try:
        # Drop privileges
        set_privileges(username, user_uid, user_gid, user_groups, user_home)

        # Start dbus-launch to get session bus
        proc = subprocess.Popen(
            'dbus-launch',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
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
        except Exception:
            pass

    except Exception as exc:
        log('E33', {'msg': str(exc)})
        exitcode = 1
    finally:
        # Log dbus/dconf info
        log('D56', {'dbus_pid': dbus_pid, 'dconf_pid': dconf_pid})

        # Cleanup processes
        if dbus_pid > 0:
            os.kill(dbus_pid, signal.SIGHUP)
        if dconf_pid > 0:
            os.kill(dconf_pid, signal.SIGTERM)
        if dbus_pid > 0:
            os.kill(dbus_pid, signal.SIGTERM)

    # Serialize result to JSON and send to parent
    try:
        os.write(wfd, json.dumps(result).encode("utf-8"))
    except Exception:
        pass
    os.close(wfd)

    sys.exit(exitcode)