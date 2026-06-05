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

import unittest
from unittest.mock import MagicMock, patch, call

import dbus as _real_dbus


class SystemdUnitInitTestCase(unittest.TestCase):

    @patch('gpoa_lib.frontend.appliers.systemd.dbus')
    @patch('gpoa_lib.frontend.appliers.systemd.log')
    def test_init_state_enable(self, mock_log, mock_dbus):
        mock_dbus.String = _real_dbus.String
        mock_dbus.Boolean = _real_dbus.Boolean
        mock_bus = MagicMock()
        mock_dbus.SystemBus.return_value = mock_bus
        mock_dbus.Interface = MagicMock(return_value=MagicMock())
        mock_manager = MagicMock()
        mock_manager.LoadUnit.return_value = '/org/freedesktop/systemd1/unit/test_2eservice'
        mock_bus.get_object.return_value = MagicMock()

        mock_dbus.Interface.side_effect = [mock_manager, MagicMock(), MagicMock()]

        from gpoa_lib.frontend.appliers.systemd import systemd_unit
        unit = systemd_unit('test.service', 1)

        self.assertEqual(unit.unit_name, 'test.service')
        self.assertEqual(unit.desired_state, 1)

    @patch('gpoa_lib.frontend.appliers.systemd.dbus')
    @patch('gpoa_lib.frontend.appliers.systemd.log')
    def test_init_state_disable(self, mock_log, mock_dbus):
        mock_dbus.String = _real_dbus.String
        mock_dbus.Boolean = _real_dbus.Boolean
        mock_bus = MagicMock()
        mock_dbus.SystemBus.return_value = mock_bus
        mock_manager = MagicMock()
        mock_manager.LoadUnit.return_value = '/org/freedesktop/systemd1/unit/test_2eservice'
        mock_dbus.Interface = MagicMock(return_value=MagicMock())

        from gpoa_lib.frontend.appliers.systemd import systemd_unit
        unit = systemd_unit('test.service', 0)

        self.assertEqual(unit.desired_state, 0)


class SystemdUnitApplyTestCase(unittest.TestCase):

    def _make_unit(self, mock_dbus, unit_name, state):
        mock_dbus.String = _real_dbus.String
        mock_dbus.Boolean = _real_dbus.Boolean
        mock_bus = MagicMock()
        mock_dbus.SystemBus.return_value = mock_bus
        mock_manager = MagicMock()
        mock_manager.LoadUnit.return_value = '/org/freedesktop/systemd1/unit/test_2eservice'
        mock_dbus.Interface = MagicMock(return_value=MagicMock())
        mock_dbus.SystemBus.return_value = mock_bus
        from gpoa_lib.frontend.appliers.systemd import systemd_unit
        unit = systemd_unit(unit_name, state)
        unit.manager = mock_manager
        return unit, mock_manager

    @patch('gpoa_lib.frontend.appliers.systemd.dbus')
    @patch('gpoa_lib.frontend.appliers.systemd.log')
    def test_apply_enable_calls_unmask_reload_enable_start(self, mock_log, mock_dbus):
        unit, manager = self._make_unit(mock_dbus, 'test.service', 1)
        manager.GetUnitFileState.return_value = 'disabled'

        unit.apply()

        manager.UnmaskUnitFiles.assert_called_once()
        manager.Reload.assert_called_once()
        manager.EnableUnitFiles.assert_called_once()
        manager.StartUnit.assert_called_once_with('test.service', 'replace')

    @patch('gpoa_lib.frontend.appliers.systemd.dbus')
    @patch('gpoa_lib.frontend.appliers.systemd.log')
    def test_apply_disable_calls_stop_disable_mask(self, mock_log, mock_dbus):
        unit, manager = self._make_unit(mock_dbus, 'test.service', 0)

        unit.apply()

        manager.StopUnit.assert_called_once_with('test.service', 'replace')
        manager.DisableUnitFiles.assert_called_once()
        manager.MaskUnitFiles.assert_called_once()

    @patch('gpoa_lib.frontend.appliers.systemd.dbus')
    @patch('gpoa_lib.frontend.appliers.systemd.log')
    def test_apply_gpupdate_service_enabled_skips_start(self, mock_log, mock_dbus):
        unit, manager = self._make_unit(mock_dbus, 'gpupdate.service', 1)
        manager.GetUnitFileState.return_value = 'enabled'

        unit.apply()

        manager.StartUnit.assert_not_called()


class SystemdUnitRestartTestCase(unittest.TestCase):

    def _make_unit(self, mock_dbus):
        mock_dbus.String = _real_dbus.String
        mock_dbus.Boolean = _real_dbus.Boolean
        mock_bus = MagicMock()
        mock_dbus.SystemBus.return_value = mock_bus
        mock_manager = MagicMock()
        mock_manager.LoadUnit.return_value = '/org/freedesktop/systemd1/unit/test_2eservice'
        mock_dbus.Interface = MagicMock(return_value=MagicMock())
        from gpoa_lib.frontend.appliers.systemd import systemd_unit
        unit = systemd_unit('test.service', 1)
        unit.manager = mock_manager
        return unit, mock_manager

    @patch('gpoa_lib.frontend.appliers.systemd.dbus')
    @patch('gpoa_lib.frontend.appliers.systemd.log')
    def test_restart_success(self, mock_log, mock_dbus):
        unit, manager = self._make_unit(mock_dbus)

        unit.restart()

        manager.RestartUnit.assert_called_once_with('test.service', 'replace')

    @patch('gpoa_lib.frontend.appliers.systemd.dbus')
    @patch('gpoa_lib.frontend.appliers.systemd.log')
    def test_restart_dbus_exception(self, mock_log, mock_dbus):
        unit, manager = self._make_unit(mock_dbus)
        mock_dbus.DBusException = _real_dbus.DBusException
        manager.RestartUnit.side_effect = _real_dbus.DBusException('fail')

        unit.restart()

        manager.RestartUnit.assert_called_once_with('test.service', 'replace')
