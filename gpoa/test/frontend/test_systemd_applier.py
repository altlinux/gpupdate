#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

import importlib
import os
import sys
import types
import unittest
import unittest.mock


class _entry:
    def __init__(self, valuename, data):
        self.valuename = valuename
        self.data = data


class _storage_stub:
    def __init__(self, entries):
        self._entries = entries

    def filter_hklm_entries(self, _branch):
        return self._entries

    def get_key_value(self, _path):
        return None


def _load_systemd_applier_module():
    if 'frontend' not in sys.modules:
        frontend_pkg = types.ModuleType('frontend')
        frontend_pkg.__path__ = [os.path.join(os.getcwd(), 'frontend')]
        sys.modules['frontend'] = frontend_pkg
    return importlib.import_module('frontend.systemd_applier')


def _load_systemd_manager_module():
    if 'frontend' not in sys.modules:
        frontend_pkg = types.ModuleType('frontend')
        frontend_pkg.__path__ = [os.path.join(os.getcwd(), 'frontend')]
        sys.modules['frontend'] = frontend_pkg
    return importlib.import_module('frontend.appliers.systemd')


class _fake_dbus_exception(Exception):
    def __init__(self, message, dbus_name):
        super().__init__(message)
        self._dbus_name = dbus_name

    def get_dbus_name(self):
        return self._dbus_name


class _fake_manager_iface:
    def __init__(self, load_exc=None):
        self.unit_path = '/org/freedesktop/systemd1/unit/demo_2eservice'
        self.load_exc = load_exc

    def LoadUnit(self, _unit_name):
        if self.load_exc:
            raise self.load_exc
        return self.unit_path


class _fake_properties_iface:
    def __init__(self, load_state='loaded', get_exc=None):
        self.load_state = load_state
        self.get_exc = get_exc

    def Get(self, _iface, _name):
        if self.get_exc:
            raise self.get_exc
        return self.load_state


class _fake_proxy:
    def __init__(self, ifaces):
        self.ifaces = ifaces


class _fake_bus:
    def __init__(self, objects):
        self._objects = objects

    def get_object(self, _bus_name, object_path):
        return self._objects[str(object_path)]


class _fake_dbus_module:
    DBusException = _fake_dbus_exception

    def __init__(self, load_state='loaded', load_exc=None, get_exc=None):
        manager_iface = _fake_manager_iface(load_exc=load_exc)
        properties_iface = _fake_properties_iface(load_state=load_state, get_exc=get_exc)
        self._objects = {
            '/org/freedesktop/systemd1': _fake_proxy({
                'org.freedesktop.systemd1.Manager': manager_iface,
            }),
            manager_iface.unit_path: _fake_proxy({
                'org.freedesktop.DBus.Properties': properties_iface,
            }),
        }

    def SystemBus(self):
        return _fake_bus(self._objects)

    def SessionBus(self):
        return _fake_bus(self._objects)

    @staticmethod
    def String(value):
        return value

    @staticmethod
    def Boolean(value):
        return value

    @staticmethod
    def Interface(proxy, interface_name=None, dbus_interface=None):
        iface_name = dbus_interface if dbus_interface is not None else interface_name
        return proxy.ifaces[iface_name]


class _fake_subprocess_result:
    def __init__(self, returncode=0, stdout='', stderr=''):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class SystemdApplierTestCase(unittest.TestCase):
    def test_run_skips_invalid_unit_name(self):
        module = _load_systemd_applier_module()
        storage = _storage_stub([
            _entry('/tmp/evil.service', '1'),
            _entry('ok.service', '1'),
        ])
        applier = module.systemd_applier(storage)

        good_unit = unittest.mock.Mock()
        with unittest.mock.patch('frontend.systemd_applier.systemd_unit', return_value=good_unit) as ctor:
            applier.run()

        ctor.assert_called_once_with('ok.service', 1)

    def test_run_handles_dbus_apply_error(self):
        module = _load_systemd_applier_module()
        from frontend.appliers.systemd import SystemdManagerError

        storage = _storage_stub([_entry('ok.service', '1')])
        applier = module.systemd_applier(storage)

        bad_unit = unittest.mock.Mock()
        bad_unit.unit_name = 'ok.service'
        bad_unit.apply.side_effect = SystemdManagerError('boom', action='start', unit='ok.service')

        with unittest.mock.patch('frontend.systemd_applier.systemd_unit', return_value=bad_unit):
            applier.run()

        bad_unit.apply.assert_called_once()

    def test_manager_exists_returns_false_for_not_found_load_state(self):
        module = _load_systemd_manager_module()
        fake_dbus = _fake_dbus_module(load_state='not-found')

        with unittest.mock.patch('frontend.appliers.systemd._import_dbus', return_value=fake_dbus):
            manager = module.SystemdManager(mode='machine')

        self.assertFalse(manager.exists('demo.service'))

    def test_manager_exists_returns_true_for_loaded_load_state(self):
        module = _load_systemd_manager_module()
        fake_dbus = _fake_dbus_module(load_state='loaded')

        with unittest.mock.patch('frontend.appliers.systemd._import_dbus', return_value=fake_dbus):
            manager = module.SystemdManager(mode='machine')

        self.assertTrue(manager.exists('demo.service'))

    def test_manager_exists_handles_no_such_unit_error(self):
        module = _load_systemd_manager_module()
        exc = _fake_dbus_exception('missing', 'org.freedesktop.systemd1.NoSuchUnit')
        fake_dbus = _fake_dbus_module(load_exc=exc)

        with unittest.mock.patch('frontend.appliers.systemd._import_dbus', return_value=fake_dbus):
            manager = module.SystemdManager(mode='machine')

        self.assertFalse(manager.exists('demo.service'))

    def test_global_manager_exists_uses_systemctl_global_cat(self):
        module = _load_systemd_manager_module()

        with unittest.mock.patch('frontend.appliers.systemd.subprocess.run') as run_mock:
            run_mock.return_value = _fake_subprocess_result(returncode=0, stdout='# /etc/systemd/user/demo.service\n')
            manager = module.SystemdManager(mode='global_user')

            self.assertTrue(manager.exists('demo.service'))
            run_mock.assert_called_once_with(
                ['systemctl', '--global', 'cat', 'demo.service'],
                stdout=module.subprocess.PIPE,
                stderr=module.subprocess.PIPE,
                text=True,
                check=False,
            )

    def test_global_manager_apply_state_ignores_now_runtime_actions(self):
        module = _load_systemd_manager_module()

        with unittest.mock.patch('frontend.appliers.systemd.subprocess.run') as run_mock:
            run_mock.side_effect = [
                _fake_subprocess_result(returncode=0),
                _fake_subprocess_result(returncode=0),
            ]
            manager = module.SystemdManager(mode='global_user')
            start_mock = unittest.mock.Mock(side_effect=AssertionError('start() must not be used for --global'))
            manager.start = start_mock

            manager.apply_state('demo.service', 'enable', now=True)

            self.assertEqual(run_mock.call_args_list, [
                unittest.mock.call(
                    ['systemctl', '--global', 'unmask', 'demo.service'],
                    stdout=module.subprocess.PIPE,
                    stderr=module.subprocess.PIPE,
                    text=True,
                    check=False,
                ),
                unittest.mock.call(
                    ['systemctl', '--global', 'enable', 'demo.service'],
                    stdout=module.subprocess.PIPE,
                    stderr=module.subprocess.PIPE,
                    text=True,
                    check=False,
                ),
            ])
            start_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
