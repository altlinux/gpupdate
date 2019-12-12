import dbus
import logging

class systemd_unit:
    __system_bus = dbus.SystemBus()
    __systemd_dbus = __system_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    __manager = dbus.Interface(__systemd_dbus, 'org.freedesktop.systemd1.Manager')

    def __init__(self, unit_name, state):
        self.unit_name = unit_name
        self.desired_state = state
        self.unit = self.__manager.LoadUnit(dbus.String(self.unit_name))
        self.unit_proxy = self.__system_bus.get_object('org.freedesktop.systemd1', str(self.unit))
        self.unit_interface = dbus.Interface(self.unit_proxy, dbus_interface='org.freedesktop.systemd1.Unit')
        self.unit_properties = dbus.Interface(self.unit_proxy, dbus_interface='org.freedesktop.DBus.Properties')

    def apply(self):
        if self.desired_state == 1:
            self.__manager.UnmaskUnitFiles([self.unit_name], dbus.Boolean(False))
            self.__manager.EnableUnitFiles([self.unit_name], dbus.Boolean(False), dbus.Boolean(True))
            self.__manager.StartUnit(self.unit_name, 'replace')
            logging.info('Starting systemd unit: {}'.format(self.unit_name))
            if self._get_state() != 'active':
                logging.error('Unable to start systemd unit {}'.format(self.unit_name))
        else:
            self.__manager.StopUnit(self.unit_name, 'replace')
            self.__manager.DisableUnitFiles([self.unit_name], dbus.Boolean(False))
            self.__manager.MaskUnitFiles([self.unit_name], dbus.Boolean(False), dbus.Boolean(True))
            logging.info('Stopping systemd unit: {}'.format(self.unit_name))
            if self._get_state() != 'stopped':
                logging.error('Unable to stop systemd unit {}'.format(self.unit_name))

    def _get_state(self):
        '''
        Get the string describing service state.
        '''
        return self.unit_properties.Get('org.freedesktop.systemd1.Unit', 'ActiveState')
