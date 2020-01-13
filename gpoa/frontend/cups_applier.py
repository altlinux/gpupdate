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
import os

from .applier_frontend import applier_frontend
from gpt.printers import json2printer
from util.rpm import is_rpm_installed
from util.logging import slogm

def storage_get_printers(storage, sid):
    '''
    Query printers configuration from storage
    '''
    printer_objs = storage.get_printers(sid)
    printers = list()

    for prnj in printer_objs:
        prn_obj = json2printer(prnj)
        printers.append(prn_obj)

    return printers

def write_printer(prn):
    '''
    Dump printer cinfiguration to disk as CUPS config
    '''
    printer_config_path = os.path.join('/etc/cups', prn.name)
    with open(printer_config_path, 'r') as f:
        print(prn.cups_config(), file=f)

class cups_applier(applier_frontend):
    def __init__(self, storage):
        self.storage = storage

    def apply(self):
        '''
        Perform configuration of printer which is assigned to computer.
        '''
        if not is_rpm_installed('cups'):
            logging.warning(slogm('CUPS is not installed: no printer settings will be deployed'))
            return

        printers = storage_get_printers(self.storage, self.storage.get_info('machine_sid'))

        if printers:
            for prn in printers:
                write_printer(prn)

class cups_applier_user(applier_frontend):
    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

    def user_context_apply(self):
        '''
        Printer configuration is the system configuration so there is
        no point in implementing this function.
        '''
        pass

    def admin_context_apply(self):
        '''
        Perform printer configuration assigned for user.
        '''
        if not is_rpm_installed('cups'):
            logging.warning(slogm('CUPS is not installed: no printer settings will be deployed'))
            return

        printers = storage_get_printers(self.storage, self.sid)

        if printers:
            for prn in printers:
                write_printer(prn)

