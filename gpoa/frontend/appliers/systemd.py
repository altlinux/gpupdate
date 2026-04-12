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

import re
import subprocess

from util.logging import log


SYSTEMD_BUS_NAME = 'org.freedesktop.systemd1'
SYSTEMD_OBJECT_PATH = '/org/freedesktop/systemd1'
SYSTEMD_MANAGER_IFACE = 'org.freedesktop.systemd1.Manager'
SYSTEMD_UNIT_IFACE = 'org.freedesktop.systemd1.Unit'
DBUS_PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'
NO_SUCH_UNIT_ERRORS = {
    'org.freedesktop.systemd1.NoSuchUnit',
    'org.freedesktop.systemd1.LoadFailed',
}
UNIT_NAME_RE = re.compile(
    r'^[A-Za-z0-9:_.@-]{1,255}\.(service|socket|timer|path|mount|automount|swap|target|device|slice|scope)$'
)


class SystemdManagerError(Exception):
    def __init__(self, message, action=None, unit=None, dbus_name=None):
        super().__init__(message)
        self.action = action
        self.unit = unit
        self.dbus_name = dbus_name


def is_valid_unit_name(unit_name):
    if not isinstance(unit_name, str):
        return False
    if not unit_name:
        return False
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in unit_name):
        return False
    if not UNIT_NAME_RE.match(unit_name):
        return False
    name_part = unit_name.rsplit('.', 1)[0]
    if name_part.startswith('-') or name_part.endswith('-'):
        return False
    return True


def _import_dbus():
    import dbus
    return dbus


class SystemdManager:
    def __init__(self, mode='machine'):
        self.mode = mode
        self.dbus = None
        self.bus = None
        self.systemd = None
        self.manager = None

        if mode == 'global_user':
            return

        self.dbus = _import_dbus()
        if mode == 'user':
            self.bus = self.dbus.SessionBus()
        else:
            self.bus = self.dbus.SystemBus()

        self.systemd = self.bus.get_object(SYSTEMD_BUS_NAME, SYSTEMD_OBJECT_PATH)
        self.manager = self.dbus.Interface(self.systemd, SYSTEMD_MANAGER_IFACE)

    def _fail(self, action, exc, unit=None):
        dbus_name = None
        if hasattr(exc, 'get_dbus_name'):
            dbus_name = exc.get_dbus_name()
        raise SystemdManagerError(str(exc), action=action, unit=unit, dbus_name=dbus_name)

    def _run_global(self, args):
        return subprocess.run(
            ['systemctl', '--global'] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def _global_output(self, result):
        output = '{}\n{}'.format(result.stdout or '', result.stderr or '').strip()
        return output or 'systemctl --global command failed'

    def _global_not_found(self, result):
        output = self._global_output(result).lower()
        return 'no files found' in output or 'not-found' in output or 'not found' in output

    def _fail_global(self, action, result, unit=None):
        raise SystemdManagerError(self._global_output(result), action=action, unit=unit)

    def _unsupported_global_action(self, action, unit=None):
        log('W48', {
            'reason': 'systemctl --global does not support runtime action {}'.format(action),
            'action': action,
            'unit': unit,
        })
        return

    def _load_unit(self, unit_name):
        try:
            return self.manager.LoadUnit(self.dbus.String(unit_name))
        except self.dbus.DBusException as exc:
            self._fail('load_unit', exc, unit=unit_name)

    def exists(self, unit_name):
        if not is_valid_unit_name(unit_name):
            return False

        if self.mode == 'global_user':
            result = self._run_global(['cat', unit_name])
            if result.returncode == 0:
                return True
            if self._global_not_found(result):
                return False
            self._fail_global('exists', result, unit=unit_name)

        try:
            unit_path = self.manager.LoadUnit(self.dbus.String(unit_name))
            proxy = self.bus.get_object(SYSTEMD_BUS_NAME, str(unit_path))
            properties = self.dbus.Interface(proxy, dbus_interface=DBUS_PROPERTIES_IFACE)
            load_state = str(properties.Get(SYSTEMD_UNIT_IFACE, 'LoadState'))
            return load_state != 'not-found'
        except self.dbus.DBusException as exc:
            if exc.get_dbus_name() in NO_SUCH_UNIT_ERRORS:
                return False
            self._fail('exists', exc, unit=unit_name)

    def _unit_properties(self, unit_name):
        unit_path = self._load_unit(unit_name)
        proxy = self.bus.get_object(SYSTEMD_BUS_NAME, str(unit_path))
        return self.dbus.Interface(proxy, dbus_interface=DBUS_PROPERTIES_IFACE)

    def active_state(self, unit_name):
        if not is_valid_unit_name(unit_name):
            return None
        if self.mode == 'global_user':
            return None
        try:
            properties = self._unit_properties(unit_name)
            return str(properties.Get(SYSTEMD_UNIT_IFACE, 'ActiveState'))
        except self.dbus.DBusException as exc:
            self._fail('active_state', exc, unit=unit_name)

    def reload(self):
        if self.mode == 'global_user':
            return
        try:
            self.manager.Reload()
        except self.dbus.DBusException as exc:
            self._fail('reload', exc)

    def start(self, unit_name):
        if self.mode == 'global_user':
            self._unsupported_global_action('start', unit=unit_name)
            return
        try:
            self.manager.StartUnit(unit_name, 'replace')
        except self.dbus.DBusException as exc:
            self._fail('start', exc, unit=unit_name)

    def stop(self, unit_name):
        if self.mode == 'global_user':
            self._unsupported_global_action('stop', unit=unit_name)
            return
        try:
            self.manager.StopUnit(unit_name, 'replace')
        except self.dbus.DBusException as exc:
            self._fail('stop', exc, unit=unit_name)

    def restart(self, unit_name):
        if self.mode == 'global_user':
            self._unsupported_global_action('restart', unit=unit_name)
            return
        try:
            self.manager.RestartUnit(unit_name, 'replace')
        except self.dbus.DBusException as exc:
            self._fail('restart', exc, unit=unit_name)

    def enable(self, unit_name):
        if self.mode == 'global_user':
            result = self._run_global(['enable', unit_name])
            if result.returncode != 0:
                self._fail_global('enable', result, unit=unit_name)
            return
        try:
            self.manager.EnableUnitFiles([unit_name], self.dbus.Boolean(False), self.dbus.Boolean(True))
        except self.dbus.DBusException as exc:
            self._fail('enable', exc, unit=unit_name)

    def disable(self, unit_name):
        if self.mode == 'global_user':
            result = self._run_global(['disable', unit_name])
            if result.returncode != 0:
                self._fail_global('disable', result, unit=unit_name)
            return
        try:
            self.manager.DisableUnitFiles([unit_name], self.dbus.Boolean(False))
        except self.dbus.DBusException as exc:
            self._fail('disable', exc, unit=unit_name)

    def mask(self, unit_name):
        if self.mode == 'global_user':
            result = self._run_global(['mask', unit_name])
            if result.returncode != 0:
                self._fail_global('mask', result, unit=unit_name)
            return
        try:
            self.manager.MaskUnitFiles([unit_name], self.dbus.Boolean(False), self.dbus.Boolean(True))
        except self.dbus.DBusException as exc:
            self._fail('mask', exc, unit=unit_name)

    def unmask(self, unit_name):
        if self.mode == 'global_user':
            result = self._run_global(['unmask', unit_name])
            if result.returncode != 0:
                self._fail_global('unmask', result, unit=unit_name)
            return
        try:
            self.manager.UnmaskUnitFiles([unit_name], self.dbus.Boolean(False))
        except self.dbus.DBusException as exc:
            self._fail('unmask', exc, unit=unit_name)

    def preset(self, unit_name):
        if self.mode == 'global_user':
            result = self._run_global(['preset', unit_name])
            if result.returncode != 0:
                self._fail_global('preset', result, unit=unit_name)
            return
        try:
            self.manager.PresetUnitFiles([unit_name], self.dbus.Boolean(False), self.dbus.Boolean(True))
        except self.dbus.DBusException as exc:
            self._fail('preset', exc, unit=unit_name)

    def get_unit_file_state(self, unit_name):
        if self.mode == 'global_user':
            result = self._run_global(['is-enabled', unit_name])
            state = (result.stdout or result.stderr or '').strip()
            if state:
                return state.splitlines()[-1].strip()
            self._fail_global('get_unit_file_state', result, unit=unit_name)
        try:
            return str(self.manager.GetUnitFileState(self.dbus.String(unit_name)))
        except self.dbus.DBusException as exc:
            self._fail('get_unit_file_state', exc, unit=unit_name)

    def apply_state(self, unit_name, state, now):
        if state == 'as_is':
            return
        if state == 'enable':
            self.unmask(unit_name)
            self.enable(unit_name)
            if now and self.mode != 'global_user':
                self.start(unit_name)
            return
        if state == 'disable':
            if now and self.mode != 'global_user':
                self.stop(unit_name)
            self.disable(unit_name)
            return
        if state == 'mask':
            if now and self.mode != 'global_user':
                self.stop(unit_name)
            self.mask(unit_name)
            return
        if state == 'unmask':
            self.unmask(unit_name)
            if now and self.mode != 'global_user':
                self.start(unit_name)
            return
        if state == 'preset':
            self.preset(unit_name)
            if now and self.mode != 'global_user':
                self.start(unit_name)
            return
        raise ValueError('Unsupported state: {}'.format(state))


class systemd_unit:
    def __init__(self, unit_name, state, manager=None):
        if not is_valid_unit_name(unit_name):
            raise ValueError('Invalid unit name: {}'.format(unit_name))
        self.unit_name = unit_name
        self.desired_state = int(state)
        if self.desired_state not in (0, 1):
            raise ValueError('Invalid desired state for {}: {}'.format(unit_name, state))
        self.manager = manager if manager is not None else SystemdManager(mode='machine')

    def apply(self):
        logdata = {'unit': self.unit_name}
        if self.desired_state == 1:
            self.manager.unmask(self.unit_name)
            self.manager.enable(self.unit_name)
            if self.unit_name == 'gpupdate.service':
                if self.manager.get_unit_file_state(self.unit_name) == 'enabled':
                    return
            self.manager.start(self.unit_name)
            log('I6', logdata)

            # In case the service has 'RestartSec' property set it
            # switches to 'activating (auto-restart)' state instead of
            # 'active' so we consider 'activating' a valid state too.
            service_state = self._get_state()

            if service_state not in ('active', 'activating'):
                service_timer_name =  self.unit_name.replace(".service", ".timer")
                if not is_valid_unit_name(service_timer_name) or not self.manager.exists(service_timer_name):
                    log('E46', logdata)
                    return
                service_state = self.manager.active_state(service_timer_name)
                if str(service_state) not in ('active', 'activating'):
                    log('E46', logdata)
        else:
            self.manager.stop(self.unit_name)
            self.manager.disable(self.unit_name)
            self.manager.mask(self.unit_name)
            log('I6', logdata)

            service_state = self._get_state()

            if service_state not in ('stopped', 'deactivating', 'inactive'):
                log('E46', logdata)

    def _get_state(self):
        '''
        Get the string describing service state.
        '''
        return self.manager.active_state(self.unit_name)

    def restart(self):
        """
        Restarts the specified unit, if available
        """
        logdata = {'unit': self.unit_name, 'action': 'restart'}
        try:
            self.manager.restart(self.unit_name)
            log('I13', logdata)
            service_state = self._get_state()
            if service_state not in ('active', 'activating'):
                log('E77', logdata)

        except SystemdManagerError as exc:
            log('E77', {**logdata, 'error': str(exc)})
