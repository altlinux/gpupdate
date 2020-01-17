#
# Copyright (C) 2019-2020 BaseALT Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import logging

from xml.etree import ElementTree
from storage import registry_factory

from samba.gp_parse.gp_pol import GPPolParser

from .logging import slogm


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
    logging.debug(slogm('Loading PReg from .pol file: {}'.format(polfile)))
    gpparser = GPPolParser()
    data = None

    with open(polfile, 'rb') as f:
        data = f.read()
        gpparser.parse(data)

    #print(gpparser.pol_file.__ndr_print__())
    return gpparser.pol_file


def preg_keymap(preg):
    pregfile = load_preg(preg)
    keymap = dict()

    for entry in pregfile.entries:
        hive_key = '{}\\{}'.format(entry.keyname, entry.valuename)
        keymap[hive_key] = entry

    return keymap


def merge_polfile(preg, sid=None):
    pregfile = load_preg(preg)
    logging.info(slogm('Loaded PReg {}'.format(preg)))
    key_map = dict()
    storage = registry_factory('registry')
    for entry in pregfile.entries:
        if not sid:
            storage.add_hklm_entry(entry)
        else:
            storage.add_hkcu_entry(entry, sid)


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

