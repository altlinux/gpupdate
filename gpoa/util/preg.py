from storage import registry_factory

import logging
import os

from samba.gpclass import get_dc_hostname
from samba.netcmd.common import netcmd_get_domain_infos_via_cldap
import samba.gpo

from xml.etree import ElementTree
from samba.gp_parse.gp_pol import GPPolParser

logging.basicConfig(level=logging.DEBUG)

def load_preg(file_path):
    '''
    Check if file extension is .xml and load preg object from XML
    file or load object as .pol file otherwise.
    '''
    if file_path.endswith('.xml'):
        return load_xml_preg(file_path)
    return load_pol_preg(file_path)

def load_xml_preg(xml_path):
    '''
    Parse XML/PReg file and return its preg object
    '''
    logging.debug('Loading PReg from XML: {}'.format(xml_path))
    gpparser = GPPolParser()
    xml_root = ElementTree.parse(xml_path).getroot()
    gpparser.load_xml(xml_root)
    gpparser.pol_file.__ndr_print__()

    return gpparser.pol_file

def load_pol_preg(polfile):
    '''
    Parse PReg file and return its preg object
    '''
    logging.debug('Loading PReg from .pol file: {}'.format(polfile))
    gpparser = GPPolParser()
    data = None

    with open(polfile, 'rb') as f:
        data = f.read()
        gpparser.parse(data)

    #print(gpparser.pol_file.__ndr_print__())
    return gpparser.pol_file

def preg2entrydict(preg, sid=None):
    '''
    Create a map (dict) of HIVE_KEY to preg.entry
    '''
    pregfile = load_preg(preg)
    logging.info('Loaded PReg {}'.format(preg))
    key_map = dict()
    storage = registry_factory('registry')

    for entry in pregfile.entries:
        if not sid:
            storage.add_hklm_entry(entry)
        else:
            storage.add_hkcu_entry(entry, sid)
        hive_key = '{}\\{}'.format(entry.keyname, entry.valuename)
        key_map[hive_key] = entry

    return key_map

def merge_polfiles(polfile_list, sid=None):
    entrydict = dict()

    for preg_file_path in polfile_list:
        entrydict.update(preg2entrydict(preg_file_path, sid))

    return entrydict

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

