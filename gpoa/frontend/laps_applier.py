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
from util.sid import WellKnown21RID
import subprocess
import ldb
import string
import secrets

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
        all_alt_keys = remove_prefix_from_keys(storage.filter_entries(self.__registry_branch), self.__registry_branch)
        self.all_keys = remove_prefix_from_keys(storage.filter_entries(self.__all_win_registry), self.__all_win_registry)
        self.all_keys.update(all_alt_keys)

        backup_directory = self.all_keys.get('BackupDirectory', None)
        if backup_directory != 2:
            self.__module_enabled = False
            print('backup_directory', backup_directory)
            return
        self.samdb = storage.get_info('samdb')
        domain_sid = self.samdb.get_domain_sid()
        self.admin_group_sid = f'{domain_sid}-{WellKnown21RID.DOMAIN_ADMINS.value}'
        self.expiration_date = self.get_expiration_date()
        self.expiration_date_int = self.get_int_time(self.expiration_date)
        self.__password = self.get_password()
        self.target_user = self.get_target_user()
        self.encryption_principal = self.get_encryption_principal()
        self.backup_directory = self.all_keys.get('BackupDirectory', None)


        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )
    def get_target_user(self):
        return self.all_keys.get('AdministratorAccountName', 'root')


    def wbinfo_check_encryption_principal(self, encryption_principal):
        try:
            domain = self.storage.get_info('domain')
            username = f'{domain}\\{encryption_principal}'
            wbinfo_cmd = ['wbinfo', '-n', username]
            output = subprocess.check_output(wbinfo_cmd)
            sid = output.split()[0].decode('utf-8')
            return sid
        except subprocess.CalledProcessError:
            wbinfo_cmd = ['wbinfo', '-s', encryption_principal]
        try:
            output = subprocess.check_output(wbinfo_cmd)
            return encryption_principal
        except:
            return None


    def get_password(self):
        password_length = self.all_keys.get('PasswordLength', 14)
        if not isinstance(password_length, int) or not (8 <= password_length <= 64):
            password_length = 14

        password_complexity = self.all_keys.get('PasswordComplexity', 4)
        if not isinstance(password_complexity, int) or not (1 <= password_complexity <= 4):
            password_complexity = 4

        char_sets = {
            1: string.ascii_uppercase,
            2: string.ascii_letters,
            3: string.ascii_letters + string.digits,
            4: string.ascii_letters + string.digits + string.punctuation
        }

        char_set = char_sets.get(password_complexity, char_sets[4])

        password = self.generate_password(char_set, password_length)

        if password_complexity >= 3 and not any(c.isdigit() for c in password):
            digit = secrets.choice(string.digits)
            position = secrets.randbelow(len(password))
            password = password[:position] + digit + password[position:]

        if password_complexity == 4 and not any(c in string.punctuation for c in password):
            special_char = secrets.choice(string.punctuation)
            position = secrets.randbelow(len(password))
            password = password[:position] + special_char + password[position:]
        return password


    def generate_password(self, char_set, length):
        password = ''.join(secrets.choice(char_set) for _ in range(length))
        return password

    def get_last_login_hours_ago(self, username):
        try:
            output = subprocess.check_output(["last", "-n", "1", username], text=True).split("\n")[0]
            parts = output.split()

            if len(parts) < 7:
                return None

            login_str = f"{parts[4]} {parts[5]} {parts[6]}"
            last_login_time = datetime.strptime(login_str, "%b %d %H:%M")
            last_login_time = last_login_time.replace(year=datetime.now().year)
            time_diff = datetime.now() - last_login_time
            return time_diff.total_seconds() // 3600

        except Exception as e:
            print('Dlog', e)
            return

    def __change_root_password(self):
        ...

    def get_encryption_principal(self):
        encryption_principal = self.all_keys.get('ADPasswordEncryptionPrincipal', None)
        sid = self.wbinfo_check_encryption_principal(encryption_principal) if encryption_principal else None
        return sid if sid else self.admin_group_sid

    def get_json_pass(self):
        password = self.__password.encode("utf-16-le") + b"\x00\x00"
        return f'{{"n":{self.target_user},"t":{self.expiration_date_int},"p":{password}}}'

    def get_expiration_date(self):
        password_age_days = self.all_keys.get('PasswordAgeDays', 0)
        return (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                + timedelta(days=int(password_age_days)))

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
            psw_json = self.get_json_pass()
            machine_name = self.storage.get_info('machine_name')
            dpapi_ng_blob = dpapi_ng.ncrypt_protect_secret(psw_json, self.encryption_principal, auth_protocol='kerberos')
            full_blob = self.get_full_blob(dpapi_ng_blob)
            mod_msg = ldb.Message()
            mod_msg.dn = self.get_computer_dn(machine_name)
            mod_msg[self.__attr_EncryptedPassword] = (ldb.MessageElement
                                            (full_blob, ldb.FLAG_MOD_REPLACE, self.__attr_EncryptedPassword))
            mod_msg[self.__attr_PasswordExpirationTime] = (ldb.MessageElement
                                            (self.expiration_date_int, ldb.FLAG_MOD_REPLACE, self.__attr_PasswordExpirationTime))

            self.samdb.modify(mod_msg)
            self.__change_root_password()
            print(f"Зашифрованный пароль для {machine_name} успешно обновлен")

        except Exception as e:
            print(f"Ошибка при работе с LDAP: {str(e)}")

    def apply(self):
        if self.__module_enabled:
            self.update_laps_password()
            print('Dlog')
        else:
            print('Dlog')
