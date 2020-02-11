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
import dbus

from .logging import slogm
from .users import is_root


class dbus_runner:
    '''
    Runs GPOA via D-Bus supplying username (if specified). This is needed
    to trigger gpoa for user running in sysadmin context.
    '''

    _bus_name = 'com.redhat.oddjob_gpupdate'
    _object_path = '/'

    def __init__(self, username=None):
        self.username = username
        system_bus = dbus.SystemBus()
        obj = system_bus.get_object(self._bus_name, self._object_path)
        self.interface = dbus.Interface(obj, self._bus_name)

    def run(self):
        #print(obj.Introspect()[0])
        if self.username:
            logging.info(slogm('Starting GPO applier for user {} via D-Bus'.format(self.username)))
            if is_root():
                result = self.interface.gpupdatefor(dbus.String(self.username))
            else:
                result = self.interface.gpupdate()
            print_dbus_result(result)
        else:
            logging.info(slogm('Starting GPO applier for computer via D-Bus'))
            result = self.interface.gpupdate_computer()
            print_dbus_result(result)
        #self.interface.Quit()


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
    logging.debug(slogm('Exit code is {}'.format(exitcode)))

    for line in message:
        print(str(line))

