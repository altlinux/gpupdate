#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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

try:
    import dbus
except ImportError:
    dbus = None

from ...util.logging import log


class systemd_manager:
    def __init__(self):
        self.bus = dbus.SystemBus()
        self.iface = dbus.Interface(
            self.bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1'),
            'org.freedesktop.systemd1.Manager',
        )
        self._reload_needed = False

    def reload(self):
        if self._reload_needed:
            self.iface.Reload()
            self._reload_needed = False

    def _mark_reload(self):
        self._reload_needed = True

    def enable_unit(self, unit_name):
        self.iface.UnmaskUnitFiles([unit_name], dbus.Boolean(False))
        self._mark_reload()
        self.iface.EnableUnitFiles([unit_name], dbus.Boolean(False), dbus.Boolean(True))
        if unit_name == 'gpupdate.service':
            if self.iface.GetUnitFileState(dbus.String(unit_name)) == 'enabled':
                return
        self.iface.StartUnit(unit_name, 'replace')

    def disable_unit(self, unit_name):
        self.iface.StopUnit(unit_name, 'replace')
        self.iface.DisableUnitFiles([unit_name], dbus.Boolean(False))
        self.iface.MaskUnitFiles([unit_name], dbus.Boolean(False), dbus.Boolean(True))
        self._mark_reload()

    def restart_unit(self, unit_name):
        try:
            self.iface.RestartUnit(unit_name, 'replace')
        except dbus.DBusException as exc:
            log('E77', {'unit': unit_name, 'action': 'restart', 'error': str(exc)})


class systemd_unit:
    def __init__(self, unit_name, state, manager=None):
        self.unit_name = unit_name
        self.desired_state = state

        if manager is not None:
            self.manager = manager.iface
            self._shared_manager = manager
            self._shared = True
        else:
            self.system_bus = dbus.SystemBus()
            obj = self.system_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
            self.manager = dbus.Interface(obj, 'org.freedesktop.systemd1.Manager')
            self._shared = False
            self.unit = self.manager.LoadUnit(dbus.String(self.unit_name))
            self.unit_proxy = self.system_bus.get_object('org.freedesktop.systemd1', str(self.unit))
            self.unit_interface = dbus.Interface(self.unit_proxy, dbus_interface='org.freedesktop.systemd1.Unit')
            self.unit_properties = dbus.Interface(self.unit_proxy, dbus_interface='org.freedesktop.DBus.Properties')

    def apply(self):
        logdata = {'unit': self.unit_name}
        if self.desired_state == 1:
            self.manager.UnmaskUnitFiles([self.unit_name], dbus.Boolean(False))
            if self._shared:
                self._shared_manager._mark_reload()
            else:
                self.manager.Reload()
            self.manager.EnableUnitFiles([self.unit_name], dbus.Boolean(False), dbus.Boolean(True))
            if self.unit_name == 'gpupdate.service':
                if self.manager.GetUnitFileState(dbus.String(self.unit_name)) == 'enabled':
                    return
            self.manager.StartUnit(self.unit_name, 'replace')
            log('I6', logdata)

            if self._shared:
                return

            service_state = self._get_state()

            if service_state not in ('active', 'activating'):
                service_timer_name = self.unit_name.replace('.service', '.timer')
                self.unit = self.manager.LoadUnit(dbus.String(service_timer_name))
                service_state = self._get_state()
                if service_state not in ('active', 'activating'):
                    log('E46', logdata)
        else:
            self.manager.StopUnit(self.unit_name, 'replace')
            self.manager.DisableUnitFiles([self.unit_name], dbus.Boolean(False))
            self.manager.MaskUnitFiles([self.unit_name], dbus.Boolean(False), dbus.Boolean(True))
            if self._shared:
                self._shared_manager._mark_reload()
            log('I6', logdata)

            if self._shared:
                return

            service_state = self._get_state()

            if service_state not in ('stopped', 'deactivating', 'inactive'):
                log('E46', logdata)

    def _get_state(self):
        return self.unit_properties.Get('org.freedesktop.systemd1.Unit', 'ActiveState')

    def restart(self):
        logdata = {'unit': self.unit_name, 'action': 'restart'}
        try:
            self.unit = self.manager.LoadUnit(dbus.String(self.unit_name))
            self.manager.RestartUnit(self.unit_name, 'replace')
            log('I13', logdata)
            if not self._shared:
                service_state = self._get_state()
                if service_state not in ('active', 'activating'):
                    log('E77', logdata)
        except dbus.DBusException as exc:
            log('E77', {**logdata, 'error': str(exc)})

