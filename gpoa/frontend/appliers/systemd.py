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

import dbus

from util.logging import log

class systemd_unit:
    def __init__(self, unit_name, state):
        self.system_bus = dbus.SystemBus()
        self.systemd_dbus = self.system_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
        self.manager = dbus.Interface(self.systemd_dbus, 'org.freedesktop.systemd1.Manager')

        self.unit_name = unit_name
        self.desired_state = state
        self.unit = self.manager.LoadUnit(dbus.String(self.unit_name))
        self.unit_proxy = self.system_bus.get_object('org.freedesktop.systemd1', str(self.unit))
        self.unit_interface = dbus.Interface(self.unit_proxy, dbus_interface='org.freedesktop.systemd1.Unit')
        self.unit_properties = dbus.Interface(self.unit_proxy, dbus_interface='org.freedesktop.DBus.Properties')

    def apply(self):
        logdata = {'unit': self.unit_name}
        if self.desired_state == 1:
            self.manager.UnmaskUnitFiles([self.unit_name], dbus.Boolean(False))
            self.manager.EnableUnitFiles([self.unit_name], dbus.Boolean(False), dbus.Boolean(True))
            if self.unit_name == 'gpupdate.service':
                if self.manager.GetUnitFileState(dbus.String(self.unit_name)) == 'enabled':
                    return
            self.manager.StartUnit(self.unit_name, 'replace')
            log('I6', logdata)

            # In case the service has 'RestartSec' property set it
            # switches to 'activating (auto-restart)' state instead of
            # 'active' so we consider 'activating' a valid state too.
            service_state = self._get_state()

            if service_state not in ('active', 'activating'):
                service_timer_name =  self.unit_name.replace(".service", ".timer")
                self.unit = self.manager.LoadUnit(dbus.String(service_timer_name))
                service_state = self._get_state()
                if service_state not in ('active', 'activating'):
                    log('E46', logdata)
        else:
            self.manager.StopUnit(self.unit_name, 'replace')
            self.manager.DisableUnitFiles([self.unit_name], dbus.Boolean(False))
            self.manager.MaskUnitFiles([self.unit_name], dbus.Boolean(False), dbus.Boolean(True))
            log('I6', logdata)

            service_state = self._get_state()

            if service_state not in ('stopped', 'deactivating', 'inactive'):
                log('E46', logdata)

    def _get_state(self):
        '''
        Get the string describing service state.
        '''
        return self.unit_properties.Get('org.freedesktop.systemd1.Unit', 'ActiveState')

