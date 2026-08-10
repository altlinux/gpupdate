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

import cups
from util.logging import log
from util.rpm import is_rpm_installed

from .applier_frontend import applier_frontend, DualContextApplier, check_enabled
from gpoa_lib.applier_result import (
    ApplierResult, ItemStatus,
    STATUS_APPLIED, STATUS_PARTIAL, STATUS_SKIPPED,
    RESULT_SUCCESS, RESULT_FAILED, RESULT_SKIPPED,
)


def storage_get_printers(storage, username=None):
    '''
    Query printers configuration from storage
    '''
    return storage.get_printers(username)

def _build_printer_uri(prn):
    '''
    Build CUPS device URI based on printer type.

    SharedPrinter → smb://server/printer
    PortPrinter   → socket://ip-address
    LocalPrinter  → ipp://path
    '''
    if prn.printer_type == 'SharedPrinter':
        path = (prn.path or '').replace('\\', '/')
        return 'smb:' + path
    elif prn.printer_type == 'PortPrinter':
        return 'socket://' + (prn.ip_address or '')
    else:
        path = (prn.path or '').replace('\\', '/')
        return 'ipp:' + path

def _get_printer_name(prn):
    '''
    Extract CUPS queue name from printer object.
    '''
    name = prn.localname or prn.name or ''
    if ' ' in (prn.path or ''):
        name = prn.path.partition(' ')[2]
    return name.replace('(', '').replace(')', '')

def connect_printer(connection, prn):
    '''
    Add printer to CUPS via IPP.
    '''
    printer_name = _get_printer_name(prn)
    printer_uri = _build_printer_uri(prn)

    connection.addPrinter(
          name=printer_name
        , info=printer_name
        , device=printer_uri
    )

class cups_applier(applier_frontend):
    __module_name = 'CUPSApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage):
        self.storage = storage
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def run(self):
        items = []
        if not is_rpm_installed('cups'):
            log('W9')
            return items
        try:
            self.cups_connection = cups.Connection()
        except Exception as exc:
            logdata = {'exc': exc}
            log('W20', logdata)
            return items
        self.printers = storage_get_printers(self.storage)

        for prn in self.printers:
            printer_name = _get_printer_name(prn)
            if prn.disabled:
                items.append(ItemStatus(key=printer_name, action='skip', result=RESULT_SKIPPED))
                continue
            try:
                connect_printer(self.cups_connection, prn)
                items.append(ItemStatus(key=printer_name, action='create', result=RESULT_SUCCESS))
            except Exception as exc:
                logdata = {'printer': printer_name, 'exc': exc}
                log('W20', logdata)
                items.append(ItemStatus(key=printer_name, action='create', result=RESULT_FAILED, detail=str(exc)))
        return items

    def apply(self):
        if self.__module_enabled:
            log('D113')
            items = self.run()
            if not items:
                return ApplierResult.skipped('cups')
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='cups', status=status, items=items)
        else:
            log('D114')
            return ApplierResult.skipped('cups')

class cups_applier_user(DualContextApplier):
    __module_name = 'CUPSApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def user_context_apply(self):
        pass

    def run(self):
        items = []
        if not is_rpm_installed('cups'):
            log('W9')
            return items
        try:
            self.cups_connection = cups.Connection()
        except Exception as exc:
            logdata = {'exc': exc}
            log('W20', logdata)
            return items
        self.printers = storage_get_printers(self.storage, self.username)

        for prn in self.printers:
            printer_name = _get_printer_name(prn)
            if prn.disabled:
                items.append(ItemStatus(key=printer_name, action='skip', result=RESULT_SKIPPED))
                continue
            try:
                connect_printer(self.cups_connection, prn)
                items.append(ItemStatus(key=printer_name, action='create', result=RESULT_SUCCESS))
            except Exception as exc:
                logdata = {'printer': printer_name, 'exc': exc}
                log('W20', logdata)
                items.append(ItemStatus(key=printer_name, action='create', result=RESULT_FAILED, detail=str(exc)))
        return items

    def apply(self, **kwargs):
        return self.admin_context_apply()

    def admin_context_apply(self):
        if self.__module_enabled:
            log('D115')
            items = self.run()
            if not items:
                return ApplierResult.skipped('cups_user')
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='cups_user', status=status, items=items)
        else:
            log('D116')
            return ApplierResult.skipped('cups_user')
