#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2025 BaseALT Ltd.
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

from .applier_frontend import (
      applier_frontend
    , check_enabled
    , check_windows_mapping_enabled
)
import struct
from datetime import datetime, timedelta
import dpapi_ng
from util.util import remove_prefix_from_keys
from util.sid import wbinfo_getsid, WellKnown21RID
import ldb

class laps_applier(applier_frontend):
    __epoch_timestamp = 11644473600  # January 1, 1970 as MS file time
    __hundreds_of_nanoseconds = 10000000
    __module_name = 'LapsApplier'
    __module_experimental = True
    __module_enabled = False
    __all_win_registry = 'SOFTWARE/Microsoft/Windows/CurrentVersion/Policies/LAPS'
    __registry_branch = 'Software/BaseALT/Policies/Laps'
    __attr_EncryptedPassword = 'msLAPS-EncryptedPassword'
    __attr_PasswordExpirationTime = 'msLAPS-PasswordExpirationTime'


    def __init__(self, storage):
        self.storage = storage
        all_alt_keys = storage.filter_entries(self.__registry_branch)
        self.all_keys = storage.filter_entries(self.__all_win_registry)
        (remove_prefix_from_keys(self.all_keys, self.__all_win_registry).update(
        remove_prefix_from_keys(all_alt_keys, self.__registry_branch)))

        self.samdb = storage.get_info('samdb')
        domain_sid = self.samdb.get_domain_sid()
        self.admin_group_sid = f'{domain_sid}-{WellKnown21RID.DOMAIN_ADMINS.value}'
        self.expiration_date = self.get_expiration_date()
        self.__password = self.get_password()
        self.target_user = self.get_target_user()

        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )
    def get_target_user(self):
        ...

    def get_password(self):
        ...

    def get_expiration_date(self):
        # something...
        tmp_time = datetime.now().replace(month=12)
        return tmp_time

    def get_int_time(self, datetime):
        epoch_timedelta = timedelta(seconds=self.__epoch_timestamp)
        new_dt = datetime + epoch_timedelta
        return int(new_dt.timestamp() * self.__hundreds_of_nanoseconds)

    def get_full_blob(self, dpapi_ng_blob):
        dt = self.get_int_time(datetime.now())
        left,right = struct.unpack('<LL',struct.pack('Q',dt))
        packed = struct.pack('<LL',right,left)
        prefix = packed + struct.pack('<i', len(dpapi_ng_blob)) + b'\x00\x00\x00\x00'
        full_blob = prefix + dpapi_ng_blob
        return full_blob

    def get_computer_dn(self, machine_name):
        search_filter = f'(sAMAccountName={machine_name})'
        results = self.samdb.search(base=self.samdb.domain_dn(), expression=search_filter, attrs=['dn'])
        return results[0]['dn']

    def update_laps_password(self):
        try:
            self.__password = self.__password.encode("utf-16-le") + b"\x00\x00"
            date_int = str(self.get_int_time(self.expiration_date))
            psw_json = '{{"n":{},"t":{},"p":{}}}'.format(self.target_user, date_int, self.__password)
            machine_name = self.storage.get_info('machine_name')
            dpapi_ng_blob = dpapi_ng.ncrypt_protect_secret(psw_json, self.admin_group_sid, auth_protocol='kerberos')
            full_blob = self.get_full_blob(dpapi_ng_blob)
            mod_msg = ldb.Message()
            mod_msg.dn = self.get_computer_dn(machine_name)
            mod_msg[self.__attr_EncryptedPassword] = ldb.MessageElement(full_blob, ldb.FLAG_MOD_REPLACE, self.__attr_EncryptedPassword)
            mod_msg[self.__attr_PasswordExpirationTime] = ldb.MessageElement(date_int, ldb.FLAG_MOD_REPLACE, self.__attr_PasswordExpirationTime)

            self.samdb.modify(mod_msg)
            print(f"Зашифрованный пароль для {machine_name} успешно обновлен")

        except Exception as e:
            print(f"Ошибка при работе с LDAP: {str(e)}")

    def apply(self):
        if self.__module_enabled:
            self.update_laps_password()
            print('Dlog')
        else:
            print('Dlog')
