import frontend.appliers
import logging

class applier_frontend:
    def __init__(self, regobj):
        pass

    def apply(self):
        pass

class control_applier(applier_frontend):
    _registry_branch = 'Software\\BaseALT\\Policies\\Control'

    def __init__(self, polfiles):
        self.polparsers = polfiles
        self.control_settings = self._get_controls(self.polparsers)
        self.controls = []
        for setting in self.control_settings:
            try:
                self.controls.append(appliers.control(setting.valuename, setting.data))
            except:
                logging.info('Unable to work with control: {}'.format(setting.valuename))
        #for e in polfile.pol_file.entries:
        #    print('{}:{}:{}:{}:{}'.format(e.type, e.data, e.valuename, e.keyname))

    def _get_controls(self, polfiles):
        '''
        Extract control entries from PReg file
        '''
        controls = []
        for parser in polfiles:
            for entry in parser.entries:
                if entry.keyname == self._registry_branch:
                    controls.append(entry)
                    logging.info('Found control setting: {}'.format(entry.valuename))
                else:
                    # Property names are taken from python/samba/gp_parse/gp_pol.py
                    logging.info('Dropped control setting: {}\\{}'.format(entry.keyname, entry.valuename))
        return controls

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for control in self.controls:
            control.set_control_status()

    def dump_settings(self):
        '''
        Write actual controls as XML and PReg files
        '''
        print('Dumping...')
        polfile = preg.file()
        polfile.header.signature = 'PReg'
        polfile.header.version = 1
        polfile.num_entries = len(self.control_settings)
        polfile.entries = self.control_settings
        print(polfile.__ndr_print__())
        
        policy_writer = GPPolParser()
        policy_writer.pol_file = polfile
        policy_writer.write_xml('test_reg.xml')
        policy_writer.write_binary('test_reg.pol')

class polkit_applier(applier_frontend):
    __registry_branch = ''
    __policy_map = {
            'Deny_All': ['99-gpoa_disk_permissions', args]
    }

    def __init__(self, polfiles):
        self.polparsers = polfiles
        self.polkit_settings = self._get_policies(self.polparsers)
        self.policies = []
        for setting in self.polkit_settings:
            if setting.keyname in __policy_map.keys():
                try:
                    self.policies.append(appliers.polkit(__policy_map[setting.keyname][0], __policy_map[setting.keyname][1]))
                except:
                    logging.info('Unable to work with control: {}'.format(setting.valuename))
        #for e in polfile.pol_file.entries:
        #    print('{}:{}:{}:{}:{}'.format(e.type, e.data, e.valuename, e.keyname))

    def _get_policies(self):
        '''
        Extract control entries from PReg file
        '''
        policies = []
        for parser in self.polparsers:
            for entry in parser.entries:
                if entry.keyname == self._registry_branch:
                    policies.append(entry)
                    logging.info('Found control setting: {}'.format(entry.valuename))
                else:
                    # Property names are taken from python/samba/gp_parse/gp_pol.py
                    logging.info('Dropped control setting: {}\\{}'.format(entry.keyname, entry.valuename))
        return policies

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for policy in self.policies:
            policy.generate()

    def dump_settings(self):
        '''
        Write actual controls as XML and PReg files
        '''
        print('Dumping...')
        polfile = preg.file()
        polfile.header.signature = 'PReg'
        polfile.header.version = 1
        polfile.num_entries = len(self.control_settings)
        polfile.entries = self.control_settings
        print(polfile.__ndr_print__())
        
        policy_writer = GPPolParser()
        policy_writer.pol_file = polfile
        policy_writer.write_xml('test_reg.xml')
        policy_writer.write_binary('test_reg.pol')


class applier:
    def __init__(self, backend):
        self.backend = backend
        self.gpvalues = self.load_values()
        logging.info('Values: {}'.format(self.gpvalues))
        capplier = control_applier(self.gpvalues)
        self.appliers = dict({ 'control': capplier, 'polkit': pkapplier })

    def load_values(self):
        '''
        This thing returns the list of samba.preg objects for
        now but it must be transformed to return registry and
        its hives to read values from.
        '''
        logging.info('Get values from backend')
        return self.backend.get_values()

    def apply_parameters(self):
        logging.info('Applying')
        self.appliers['control'].apply()
        self.appliers['polkit'].apply()
        # This thing dumps Registry.pol files to disk from data structures
        #print('Writing settings to file')
        #self.appliers['control'].dump_settings()

