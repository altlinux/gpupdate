import dbus

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
            logging.info('Starting GPO applier for user {} via D-Bus'.format(self.username))
            result = self.interface.gpupdatefor(dbus.String(self.username))
            print_dbus_result(result)
        else:
            result = self.interface.gpupdate()
            print_dbus_result(result)
        #self.interface.Quit()

def is_oddjobd_gpupdate_accessible():
    '''
    Check is oddjobd is running via systemd so it will be possible
    to run gpoa via D-Bus
    '''
    try:
        system_bus = dbus.SystemBus()
        systemd_bus = system_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
        systemd_interface = dbus.Interface(systemd_bus, 'org.freedesktop.systemd1.Manager')
        oddjobd_unit = systemd_interface.GetUnit(dbus.String('oddjobd.service'))

        oddjobd_proxy = system_bus.get_object('org.freedesktop.systemd1', str(oddjobd_unit))
        oddjobd_properties = dbus.Interface(oddjobd_proxy, dbus_interface='org.freedesktop.DBus.Properties')

        # Check if oddjobd service is running
        oddjobd_state = oddjobd_properties.Get('org.freedesktop.systemd1.Unit', 'ActiveState')

        # Check if oddjobd_gpupdate is accesssible
        oddjobd_gpupdate = system_bus.get_object('com.redhat.oddjob_gpupdate', '/')
        oddjobd_upupdate_interface = dbus.Interface(oddjobd_gpupdate, 'com.redhat.oddjob_gpupdate')
        #oddjobd_upupdate_interface.gpupdate()

        if oddjobd_state == 'active':
            return True
    except:
        pass

    return False

def print_dbus_result(result):
    '''
    Print lines returned by oddjobd (called via D-Bus) to stdout.
    '''
    exitcode = result[0]
    message = result[1:]
    logging.debug('Exit code is {}'.format(exitcode))

    for line in message:
        print(str(line))

