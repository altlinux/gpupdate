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

import dbus

from .logging import log
from .users import is_root


class dbus_runner:
    '''
    Runs GPOA via D-Bus supplying username (if specified). This is needed
    to trigger gpoa for user running in sysadmin context.
    '''

    _redhat_bus_name = 'com.redhat.oddjob_gpupdate'
    _basealt_bus_name = 'ru.basealt.oddjob_gpupdate'
    # Interface name is equal to bus name.
    _redhat_interface_name = 'com.redhat.oddjob_gpupdate'
    _basealt_interface_name = 'ru.basealt.oddjob_gpupdate'
    _object_path = '/'
    # The timeout is in milliseconds. The default is -1 which is
    # DBUS_TIMEOUT_USE_DEFAULT which is 25 seconds. There is also
    # DBUS_TIMEOUT_INFINITE constant which is equal to INT32_MAX or
    # 0x7ffffff (largest 32-bit integer).
    #
    # It was decided to set the timeout to 10 minutes which must be
    # sufficient to replicate and apply all recognizable GPOs.
    _synchronous_timeout = 600000

    def __init__(self, username=None):
        self.username = username
        self.system_bus = dbus.SystemBus()
        self.bus_name = self._basealt_bus_name
        self.interface_name = self._basealt_interface_name
        self.check_dbus()

    def check_dbus(self):
        try:
            # Check privileged operations bus
            log('D900', {'bus_name': self.bus_name})
            self.system_bus.get_object(self.bus_name, '/')
            return

        except dbus.exceptions.DBusException as exc:
            if exc.get_dbus_name() != 'org.freedesktop.DBus.Error.ServiceUnknown':
                raise exc

        self.bus_name = self._redhat_bus_name
        self.interface_name = self._redhat_interface_name

        # Try to check alternative privileged operations bus
        log('W902', {'origin_bus_name': self._basealt_interface_name, 'bus_name': self.bus_name})
        self.system_bus.get_object(self.bus_name, '/')

    def run(self):
        if self.username:
            logdata = dict({'username': self.username})
            log('D6', logdata)
            if is_root():
                # oddjobd-gpupdate's ACL allows access to this method
                # only for superuser. This method is called via PAM
                # when user logs in.
                try:
                    result = self.system_bus.call_blocking(self.bus_name,
                        self._object_path,
                        self.interface_name,
                        'gpupdatefor',
                        's',
                        [self.username],
                        timeout=self._synchronous_timeout)
                    print_dbus_result(result)
                except dbus.exceptions.DBusException as exc:
                    logdata = dict()
                    logdata['username'] = self.username
                    log('E23', logdata)
                    raise exc
            else:
                try:
                    result = self.system_bus.call_blocking(self.bus_name,
                        self._object_path,
                        self.interface_name,
                        'gpupdate',
                        None,
                        [],
                        timeout=self._synchronous_timeout)
                    print_dbus_result(result)
                except dbus.exceptions.DBusException as exc:
                    logdata = dict({'error': str(exc)})
                    log('E21', logdata)
                    raise exc
        else:
            log('D11')
            try:
                result = self.system_bus.call_blocking(self.bus_name,
                    self._object_path,
                    self.interface_name,
                    'gpupdate_computer',
                    None,
                    # The following positional parameter is called "args".
                    # There is no official documentation for it.
                    [],
                    timeout=self._synchronous_timeout)
                print_dbus_result(result)
            except dbus.exceptions.DBusException as exc:
                print(exc)
                logdata = dict({'error': str(exc)})
                log('E22', logdata)
                raise exc


def start_gpupdate_user():
    '''
    Make gpupdate-user.service "runtime-enabled" and start it. This
    function is needed in order to perform user service start in case
    pam_systemd.so is not present in PAM stack.
    '''
    unit_name = 'gpupdate-user.service'
    session_bus = dbus.SessionBus()

    systemd_user_bus = session_bus.get_object(
        'org.freedesktop.systemd1', '/org/freedesktop/systemd1')

    systemd_user_interface = dbus.Interface(
        systemd_user_bus, dbus_interface='org.freedesktop.systemd1.Manager')

    gpupdate_user_unit = systemd_user_interface.GetUnit(dbus.String(unit_name))
    job = systemd_user_interface.StartUnit(unit_name, 'replace')
    #job = manager.StartTransientUnit('noname', 'replace', properties, [])


def is_oddjobd_gpupdate_accessible():
    '''
    Check if oddjobd is running via systemd so it will be possible
    to run gpoa via D-Bus
    '''
    oddjobd_accessible = False

    try:
        system_bus = dbus.SystemBus()

        systemd_bus = system_bus.get_object(
            'org.freedesktop.systemd1', '/org/freedesktop/systemd1')

        systemd_interface = dbus.Interface(systemd_bus, 'org.freedesktop.systemd1.Manager')
        oddjobd_unit = systemd_interface.GetUnit(dbus.String('oddjobd.service'))

        oddjobd_proxy = system_bus.get_object('org.freedesktop.systemd1', str(oddjobd_unit))

        oddjobd_properties = dbus.Interface(oddjobd_proxy,
            dbus_interface='org.freedesktop.DBus.Properties')

        # Check if oddjobd service is running
        oddjobd_state = oddjobd_properties.Get('org.freedesktop.systemd1.Unit', 'ActiveState')

        # Check if oddjobd_gpupdate is accesssible
        try:
            oddjobd_gpupdate = system_bus.get_object('ru.basealt.oddjob_gpupdate', '/')
            oddjobd_upupdate_interface = dbus.Interface(oddjobd_gpupdate, 'ru.basealt.oddjob_gpupdate')
        except dbus.exceptions.DBusException as exc:
            if exc.get_dbus_name() != '.org.freedesktop.DBus.Error.ServiceUnknown':
                oddjobd_gpupdate = system_bus.get_object('com.redhat.oddjob_gpupdate', '/')
                oddjobd_upupdate_interface = dbus.Interface(oddjobd_gpupdate, 'com.redhat.oddjob_gpupdate')
                #oddjobd_upupdate_interface.gpupdate()

        if oddjobd_state == 'active':
            oddjobd_accessible = True
    except:
        pass

    return oddjobd_accessible


def print_dbus_result(result):
    '''
    Print lines returned by oddjobd (called via D-Bus) to stdout.
    '''
    exitcode = result[0]
    message = result[1:]
    logdata = dict({'retcode': exitcode})
    log('D12', logdata)

    for line in message:
        if line: print(str(line))


class dbus_session:
    def __init__(self):
        try:
            self.session_bus = dbus.SessionBus()
            self.session_dbus = self.session_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
            self.session_iface = dbus.Interface(self.session_dbus, 'org.freedesktop.DBus')
        except dbus.exceptions.DBusException as exc:
            logdata = dict({'error': str(exc)})
            log('E31', logdata)
            raise exc

    def get_connection_pid(self, connection):
        pid = -1
        try:
            pid = self.session_iface.GetConnectionUnixProcessID(connection)
            log('D57', {"pid": pid})
        except dbus.exceptions.DBusException as exc:
            if exc.get_dbus_name() != 'org.freedesktop.DBus.Error.NameHasNoOwner':
                logdata = dict({'error': str(exc)})
                log('E32', logdata)
                raise exc
            log('D58', {'connection': connection})
        return int(pid)
