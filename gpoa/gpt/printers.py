#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
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

import json

from util.xml import get_xml_root

def read_printers(printers_file):
    '''
    Read printer configurations from Printer.xml
    '''
    printers = list()

    for prn in get_xml_root(printers_file):
        prn_obj = printer(prn.tag, prn.get('name'), prn.get('status'))
        if 'PortPrinter' == prn.tag:
            prn_obj.set_ip(prn.get('ipAddress'))

        props = prn.find('Properties')
        prn_obj.set_location(props.get('location'))
        prn_obj.set_localname(props.get('localName'))
        prn_obj.set_comment(props.get('comment'))
        prn_obj.set_path(props.get('path'))

        printers.append(prn_obj)

    return printers

def merge_printers(storage, sid, printer_objects, policy_name):
    for device in printer_objects:
        storage.add_printer(sid, device, policy_name)

def json2printer(json_str):
    '''
    Build printer object out of string-serialized JSON.
    '''
    json_obj = json.loads(json_str)

    prn = printer(json_obj['type'], json_obj['name'], json_obj['status'])
    prn.set_location(json_obj['location'])
    prn.set_localname(json_obj['localname'])
    prn.set_comment(json_obj['comment'])
    prn.set_path(json_obj['path'])
    prn.set_ip(json_obj['ip'])

    return prn

class printer:
    def __init__(self, ptype, name, status):
        '''
        ptype may be one of:
        * LocalPrinter - IPP printer
        * SharedPrinter - Samba printer
        * PortPrinter
        '''
        self.printer_type = ptype
        self.name = name
        self.status = status
        self.location = None
        self.localname = None
        self.comment = None
        self.path = None
        self.ip_address = None

    def set_location(self, location):
        '''
        Location property usually is a string description of
        geographical location where printer is residing.
        '''
        self.location = location

    def set_localname(self, localname):
        self.localname = localname

    def set_comment(self, comment):
        self.comment = comment

    def set_path(self, path):
        self.path = path

    def set_ip(self, ipaddr):
        self.ip_address = ipaddr

    def to_json(self):
        '''
        Return string-serialized JSON representation of the object.
        '''
        printer = dict()
        printer['type'] = self.printer_type
        printer['name'] = self.name
        printer['status'] = self.status
        printer['location'] = self.location
        printer['localname'] = self.localname
        printer['comment'] = self.comment
        printer['path'] = self.path
        printer['ip'] = self.ip_address

        # Nesting JSON object into JSON object makes it easier to add
        # metadata if needed.
        config = dict()
        config['printer'] = printer

        return json.dumps(config)

    def cups_config(self):
        '''
        Return string-serialized CUPS configuration.
        '''
        config = ''
        return config

