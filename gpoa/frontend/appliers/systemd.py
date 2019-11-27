import dbus
import logging

logging.basicConfig(level=logging.DEBUG)

class systemd_unit:
    __system_bus = dbus.SystemBus()
    __systemd_dbus = __system_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
    __manager = dbus.Interface(__systemd_dbus, 'org.freedesktop.systemd1.Manager')

    def __init__(self, unit_name, state):
        self.unit_name = unit_name
        self.desired_state = state
        self.unit = self.__manager.LoadUnit(self.unit_name)
        self.unit_proxy = self.__system_bus.get_object('org.freedesktop.systemd1', str(self.unit))
        self.unit_interface = dbus.Interface(self.unit_proxy, dbus_interface='org.freedesktop.systemd1.Unit')

    def apply(self):
        if self.desired_state == 1:
            self.__manager.UnmaskUnitFiles([self.unit_name], dbus.Boolean(True))
            self.__manager.EnableUnitFiles([self.unit_name], dbus.Boolean(True), dbus.Boolean(True))
            self.__manager.StartUnit(self.unit_name, 'replace')
            logging.info('Starting systemd unit: {}'.format(self.unit_name))
        else:
            self.__manager.MaskUnitFiles([self.unit_name], dbus.Boolean(True), dbus.Boolean(True))
            self.__manager.DisableUnitFiles([self.unit_name], dbus.Boolean(True))
            self.__manager.StopUnit(self.unit_name, 'replace')
            logging.info('Stopping systemd unit: {}'.format(self.unit_name))

