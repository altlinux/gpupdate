import frontend.appliers
import logging
from xml.etree import ElementTree

from samba.gp_parse.gp_pol import GPPolParser

class applier_frontend:
    def __init__(self, regobj):
        pass

    def apply(self):
        pass

class entry:
    def __init__(self, e_keyname, e_valuename, e_type, e_data):
        self.keyname = e_keyname
        self.valuename = e_valuename
        self.type = e_type
        self.data = e_data

def preg2entries(preg_obj):
    entries = []
    for elem in prej_obj.entries:
        entry_obj = entry(elem.keyname, elem.valuename, elem.type, elem.data)
        entries.append(entry_obj)
    return entries

def load_xml_preg(xml_path):
    '''
    Parse PReg file and return its preg object
    '''
    logging.info('Loading PReg from XML: {}'.format(xml_path))
    gpparser = GPPolParser()
    xml_root = ElementTree.parse(xml_path).getroot()
    gpparser.load_xml(xml_root)
    gpparser.pol_file.__ndr_print__()
    return gpparser.pol_file

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
    _registry_branch = 'Software\\Policies\\Microsoft\\Windows\\RemovableStorageDevices'
    __policy_map = {
            'Deny_All': ['99-gpoa_disk_permissions', { 'Deny_All': 0 }]
    }

    def __init__(self, polfiles):
        self.polparsers = polfiles
        self.polkit_settings = self._get_policies()
        self.policies = []
        for setting in self.polkit_settings:
            if setting.valuename in self.__policy_map.keys() and setting.keyname == self._registry_branch:
                logging.info('Found key: {}, file: {} and value: {}'.format(setting.keyname, self.__policy_map[setting.valuename][0], self.__policy_map[setting.valuename][1]))
                #try:
                self.__policy_map[setting.valuename][1][setting.valuename] = setting.data
                self.policies.append(appliers.polkit(self.__policy_map[setting.valuename][0], self.__policy_map[setting.valuename][1]))
                #except Exception as exc:
                #    print(exc)
                #    logging.info('Unable to work with PolicyKit setting: {}'.format(setting.valuename))
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
                    logging.info('Found PolicyKit setting: {}'.format(entry.valuename))
                else:
                    # Property names are taken from python/samba/gp_parse/gp_pol.py
                    logging.info('Dropped setting: {}\\{}'.format(entry.keyname, entry.valuename))
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
    def __init__(self, sid, backend):
        self.backend = backend
        self.gpvalues = self.load_values()
        logging.info('Values: {}'.format(self.gpvalues))
        capplier = control_applier(self.gpvalues)
        pkapplier = polkit_applier(self.gpvalues)
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

