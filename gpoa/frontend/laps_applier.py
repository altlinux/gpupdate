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
    applier_frontend,
    check_enabled
)
import struct
from datetime import datetime, timedelta
import dpapi_ng
from util.util import remove_prefix_from_keys, check_local_user_exists
from util.sid import WellKnown21RID
import subprocess
import ldb
import string
import secrets
import os
import psutil
from util.logging import log

class laps_applier(applier_frontend):
    """
    LAPS (Local Administrator Password Solution) implementation for managing
    and automatically rotating administrator passwords.
    """

    # Time calculation constants

    # Number of seconds between the Windows epoch (1601-01-01 00:00:00 UTC)
    # and the Unix epoch (1970-01-01 00:00:00 UTC).
    # Used to convert between Unix timestamps and Windows FileTime.
    _EPOCH_TIMESTAMP = 11644473600
    # Number of 100-nanosecond intervals per second.
    # Used to convert seconds to Windows FileTime format.
    _HUNDREDS_OF_NANOSECONDS = 10000000
    # Number of 100-nanosecond intervals in one day
    _DAY_FLOAT = 8.64e11

    # Module configuration
    __module_name = 'LapsApplier'
    __module_experimental = True
    __module_enabled = False

    # Registry paths
    _WINDOWS_REGISTRY_PATH = 'SOFTWARE/Microsoft/Windows/CurrentVersion/Policies/LAPS/'
    _ALT_REGISTRY_PATH = 'Software/BaseALT/Policies/Laps/'

    # LDAP attributes
    _ATTR_ENCRYPTED_PASSWORD = 'msLAPS-EncryptedPassword'
    _ATTR_PASSWORD_EXPIRATION_TIME = 'msLAPS-PasswordExpirationTime'

    # dconf key for password modification time
    _KEY_PASSWORD_LAST_MODIFIED = '/Software/BaseALT/Policies/Laps/PasswordLastModified/'

    # Password complexity levels
    _PASSWORD_COMPLEXITY = {
        1: string.ascii_uppercase,
        2: string.ascii_letters,
        3: string.ascii_letters + string.digits,
        4: string.ascii_letters + string.digits + string.punctuation
    }

    # Post-authentication actions
    _ACTION_NONE = 0
    _ACTION_CHANGE_PASSWORD = 1
    _ACTION_TERMINATE_SESSIONS = 3
    _ACTION_REBOOT = 5

    def __init__(self, storage):
        """
        Initialize the LAPS applier with configuration from registry.

        Args:
            storage: Storage object containing registry entries and system information
        """
        self.storage = storage

        # Load registry configuration
        if not self._load_configuration():
            self.__module_enabled = False
            return

        if not self._check_requirements():
            log('W29')
            self.__module_enabled = False
            return

        # Initialize system connections and parameters
        self._initialize_system_parameters()

        # Check if module is enabled in configuration
        self.__module_enabled = check_enabled(
            self.storage,
            self.__module_name,
            self.__module_experimental
        )

    def _load_configuration(self):
        """Load configuration settings from registry."""
        alt_keys = remove_prefix_from_keys(
            self.storage.filter_entries(self._ALT_REGISTRY_PATH),
            self._ALT_REGISTRY_PATH
        )
        windows_keys = remove_prefix_from_keys(
            self.storage.filter_entries(self._WINDOWS_REGISTRY_PATH),
            self._WINDOWS_REGISTRY_PATH
        )

        # Combine configurations with BaseALT taking precedence
        self.config = windows_keys
        self.config.update(alt_keys)

        # Extract commonly used configuration parameters
        self.backup_directory = self.config.get('BackupDirectory', None)
        self.encryption_enabled = self.config.get('ADPasswordEncryptionEnabled', 1)
        self.password_expiration_protection = self.config.get('PasswordExpirationProtectionEnabled', 1)
        self.password_age_days = self.config.get('PasswordAgeDays', 30)
        self.post_authentication_actions = self.config.get('PostAuthenticationActions', 3)
        self.post_authentication_reset_delay = self.config.get('PostAuthenticationResetDelay', 24)
        name = self.config.get('AdministratorAccountName', 'root')
        if check_local_user_exists(name):
            self.target_user = name
        else:
            log('W36')
            return False
        return True

    def _check_requirements(self):
        """
        Check if the necessary requirements are met for the module to operate.

        Returns:
            bool: True if requirements are met, False otherwise
        """
        if self.backup_directory != 2 and self.encryption_enabled == 1:
            logdata = dict()
            logdata['backup_directory'] = self.backup_directory
            logdata['encryption_enabled'] = self.encryption_enabled
            log('D223', logdata)
            return False
        return True

    def _initialize_system_parameters(self):
        """Initialize system parameters and connections."""
        # Set up LDAP connections
        self.samdb = self.storage.get_info('samdb')
        self.domain_sid = self.samdb.get_domain_sid()
        self.domain_dn = self.samdb.domain_dn()
        self.computer_dn = self._get_computer_dn()
        self.admin_group_sid = f'{self.domain_sid}-{WellKnown21RID.DOMAIN_ADMINS.value}'

        # Set up time parameters
        self.expiration_date = self._get_expiration_date()
        self.expiration_date_int = self._convert_to_filetime(self.expiration_date)
        self.current_time_int = self._convert_to_filetime(datetime.now())

        # Get current system state
        self.expiration_time_attr = self._get_expiration_time_attr()
        self.pass_last_mod_int = self._read_dconf_pass_last_mod()
        self.encryption_principal = self._get_encryption_principal()
        self.last_login_hours_ago = self._get_last_login_hours_ago()

    def _get_computer_dn(self):
        """
        Get the Distinguished Name of the computer account.

        Returns:
            str: Computer's distinguished name in LDAP
        """
        machine_name = self.storage.get_info('machine_name')
        search_filter = f'(sAMAccountName={machine_name})'
        results = self.samdb.search(base=self.domain_dn, expression=search_filter, attrs=['dn'])
        return results[0]['dn']

    def _get_encryption_principal(self):
        """
        Get the encryption principal for password encryption.

        Returns:
            str: SID of the encryption principal
        """
        encryption_principal = self.config.get('ADPasswordEncryptionPrincipal', None)
        if not encryption_principal:
            return self.admin_group_sid

        return self._verify_encryption_principal(encryption_principal)

    def _verify_encryption_principal(self, principal_name):
        """
        Verify the encryption principal exists and get its SID.

        Args:
            principal_name: Principal name to verify

        Returns:
            str: SID of the encryption principal if found, or admin group SID as fallback
        """
        try:
            # Try to resolve as domain\\user format
            domain = self.storage.get_info('domain')
            username = f'{domain}\\{principal_name}'
            output = subprocess.check_output(['wbinfo', '-n', username])
            sid = output.split()[0].decode('utf-8')
            return sid
        except subprocess.CalledProcessError:
            # Try to resolve directly as SID
            try:
                output = subprocess.check_output(['wbinfo', '-s', principal_name])
                return principal_name
            except subprocess.CalledProcessError:
                # Fallback to admin group SID
                logdata = dict()
                logdata['principal_name'] = principal_name
                log('W30', logdata)
                return self.admin_group_sid

    def _get_expiration_date(self, base_time=None):
        """
        Calculate the password expiration date.

        Args:
            base_time: Optional datetime to base calculation on, defaults to now

        Returns:
            datetime: Password expiration date
        """
        base = base_time or datetime.now()
        # Set to beginning of day and add password age
        return (base.replace(hour=0, minute=0, second=0, microsecond=0) +
                timedelta(days=int(self.password_age_days)))

    def _convert_to_filetime(self, dt):
        """
        Convert datetime to Windows filetime format (100ns intervals since 1601-01-01).

        Args:
            dt: Datetime to convert

        Returns:
            int: Windows filetime integer
        """
        epoch_timedelta = timedelta(seconds=self._EPOCH_TIMESTAMP)
        new_dt = dt + epoch_timedelta
        return int(new_dt.timestamp() * self._HUNDREDS_OF_NANOSECONDS)

    def _get_expiration_time_attr(self):
        """
        Get the current password expiration time from LDAP.

        Returns:
            int: Password expiration time as integer, or 0 if not found
        """
        try:
            res = self.samdb.search(
                base=self.computer_dn,
                scope=ldb.SCOPE_BASE,
                expression="(objectClass=*)",
                attrs=[self._ATTR_PASSWORD_EXPIRATION_TIME]
            )
            return int(res[0].get(self._ATTR_PASSWORD_EXPIRATION_TIME, 0)[0])
        except Exception as exc:
            logdata = dict()
            logdata['exc'] = exc
            log('W31', logdata)
            return 0

    def _read_dconf_pass_last_mod(self):
        """
        Read the password last modified time from dconf.

        Returns:
            int: Timestamp of last password modification or current time if not found
        """
        try:
            key_path = self._KEY_PASSWORD_LAST_MODIFIED + self.target_user
            last_modified = subprocess.check_output(
                ['dconf', 'read', key_path],
                text=True
            ).strip().strip("'\"")
            return int(last_modified)
        except Exception as exc:
            logdata = dict()
            logdata['exc'] = exc
            log('W32', logdata)
            return self.current_time_int

    def _write_dconf_pass_last_mod(self):
        """
        Write the password last modified time to dconf.
        """
        try:
            # Ensure dbus session is available
            self._ensure_dbus_session()

            # Write current time to dconf
            key_path = self._KEY_PASSWORD_LAST_MODIFIED + self.target_user
            last_modified = f'"{self.current_time_int}"'
            subprocess.check_output(['dconf', 'write', key_path, last_modified])
            log('D222')
        except Exception as exc:
            logdata = dict()
            logdata['exc'] = exc
            log('W28', logdata)

    def _ensure_dbus_session(self):
        """Ensure a D-Bus session is available for dconf operations."""
        dbus_address = os.getenv("DBUS_SESSION_BUS_ADDRESS")
        if not dbus_address:
            result = subprocess.run(
                ["dbus-daemon", "--fork", "--session", "--print-address"],
                capture_output=True,
                text=True
            )
            dbus_address = result.stdout.strip()
            os.environ["DBUS_SESSION_BUS_ADDRESS"] = dbus_address

    def _get_last_login_hours_ago(self):
        """
        Get the number of hours since the user's last login.

        Returns:
            int: Hours since last login, or 0 if error or no login found
        """
        logdata = dict()
        logdata['target_user'] = self.target_user
        try:
            output = subprocess.check_output(
                ["last", "-n", "1", self.target_user],
                env={'LANG':'C'},
                text=True
            ).split("\n")[0]

            parts = output.split()
            if len(parts) < 7:
                return 0

            # Parse login time
            login_str = f"{parts[4]} {parts[5]} {parts[6]}"
            last_login_time = datetime.strptime(login_str, "%b %d %H:%M")
            last_login_time = last_login_time.replace(year=datetime.now().year)

            # Calculate hours difference
            time_diff = datetime.now() - last_login_time
            hours_ago = int(time_diff.total_seconds() // 3600)
            logdata['hours_ago'] = hours_ago
            log('D224', logdata)
            return hours_ago
        except Exception as exc:
            logdata['exc'] = exc
            log('W33', logdata)
            return 0

    def _get_changed_password_hours_ago(self):
        """
        Calculate how many hours ago the password was last changed.

        Returns:
            int: Hours since password was last changed, or 0 if error
        """
        logdata = dict()
        logdata['target_user'] = self.target_user
        try:
            diff_time = self.current_time_int - self.pass_last_mod_int
            hours_difference = diff_time // 3.6e10
            hours_ago = int(hours_difference)
            logdata['hours_ago'] = hours_ago
            log('D225', logdata)
            return hours_ago
        except Exception as exc:
            logdata['exc'] = exc
            log('W34', logdata)
            return 0

    def _generate_password(self):
        """
        Generate a secure password based on policy settings.

        Returns:
            str: Generated password meeting complexity requirements
        """
        # Get password length from config
        password_length = self.config.get('PasswordLength', 14)
        if not isinstance(password_length, int) or not (8 <= password_length <= 64):
            password_length = 14

        # Get password complexity from config
        password_complexity = self.config.get('PasswordComplexity', 4)
        if not isinstance(password_complexity, int) or not (1 <= password_complexity <= 4):
            password_complexity = 4

        # Get character set based on complexity
        char_set = self._PASSWORD_COMPLEXITY.get(password_complexity, self._PASSWORD_COMPLEXITY[4])

        # Generate initial password
        password = ''.join(secrets.choice(char_set) for _ in range(password_length))

        # Ensure password meets complexity requirements
        if password_complexity >= 3 and not any(c.isdigit() for c in password):
            # Add a digit if required but missing
            digit = secrets.choice(string.digits)
            position = secrets.randbelow(len(password))
            password = password[:position] + digit + password[position:]

        if password_complexity == 4 and not any(c in string.punctuation for c in password):
            # Add a special character if required but missing
            special_char = secrets.choice(string.punctuation)
            position = secrets.randbelow(len(password))
            password = password[:position] + special_char + password[position:]

        return password

    def _get_json_password_data(self, password):
        """
        Format password information as JSON.

        Args:
            password: The password

        Returns:
            str: JSON formatted password information
        """
        return f'{{"n":"{self.target_user}","t":"{self.expiration_date_int}","p":"{password}"}}'

    def _create_password_blob(self, password):
        """
        Create encrypted password blob for LDAP storage.

        Args:
            password: Password to encrypt

        Returns:
            bytes: Encrypted password blob
        """
        # Create JSON data and encode as UTF-16LE with null terminator
        json_data = self._get_json_password_data(password)
        password_bytes = json_data.encode("utf-16-le") + b"\x00\x00"

        # Encrypt the password
        dpapi_blob = dpapi_ng.ncrypt_protect_secret(
            password_bytes,
            self.encryption_principal,
            auth_protocol='kerberos'
        )

        # Create full blob with metadata
        return self._add_blob_metadata(dpapi_blob)

    def _add_blob_metadata(self, dpapi_blob):
        """
        Add metadata to the encrypted password blob.

        Args:
            dpapi_blob: Encrypted password blob

        Returns:
            bytes: Complete blob with metadata
        """
        # Convert timestamp to correct format
        left, right = struct.unpack('<LL', struct.pack('Q', self.current_time_int))
        packed = struct.pack('<LL', right, left)

        # Add blob length and padding
        prefix = packed + struct.pack('<i', len(dpapi_blob)) + b'\x00\x00\x00\x00'

        # Combine metadata and encrypted blob
        return prefix + dpapi_blob

    def _change_user_password(self, new_password):
        """
        Change the password for the target user.

        Args:
            new_password: New password to set

        Returns:
            bool: True if password was changed successfully, False otherwise
        """
        logdata = dict()
        logdata['target_use'] = self.target_user
        try:
            # Use chpasswd to change the password
            process = subprocess.Popen(
                ["chpasswd"],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(f"{self.target_user}:{new_password}")

            # Record the time of change
            self._write_dconf_pass_last_mod()
            log('D221', logdata)
            return True
        except Exception as exc:
            logdata['exc'] = exc
            log('W27', logdata)
            return False

    def _update_ldap_password(self, encrypted_blob):
        """
        Update the encrypted password and expiration time in LDAP.

        Args:
            encrypted_blob: Encrypted password blob

        Returns:
            bool: True if LDAP was updated successfully, False otherwise
        """
        logdata = dict()
        logdata['computer_dn'] = self.computer_dn
        try:
            # Create LDAP modification message
            mod_msg = ldb.Message()
            mod_msg.dn = self.computer_dn

            # Update password blob
            mod_msg[self._ATTR_ENCRYPTED_PASSWORD] = ldb.MessageElement(
                encrypted_blob,
                ldb.FLAG_MOD_REPLACE,
                self._ATTR_ENCRYPTED_PASSWORD
            )

            # Update expiration time
            mod_msg[self._ATTR_PASSWORD_EXPIRATION_TIME] = ldb.MessageElement(
                str(self.expiration_date_int),
                ldb.FLAG_MOD_REPLACE,
                self._ATTR_PASSWORD_EXPIRATION_TIME
            )

            # Perform the LDAP modification
            self.samdb.modify(mod_msg)
            log('D226', logdata)
            return True
        except Exception as exc:
            logdata['exc'] = exc
            log('E75', logdata)
            return False

    def _should_update_password(self):
        """
        Determine if the password should be updated based on policy.

        Returns:
            tuple: (bool: update needed, bool: perform post-action)
        """
        # Check if password has expired
        if not self._is_password_expired():
            # Password not expired, check if post-login action needed
            return self._check_post_login_action()

        # Password has expired, update needed
        return True, False

    def _is_password_expired(self):
        """
        Check if the password has expired according to policy.

        Returns:
            bool: True if password has expired, False otherwise
        """
        # Case 1: No expiration protection, check LDAP attribute
        if not self.password_expiration_protection:
            if self.expiration_time_attr > self.current_time_int:
                return False
        # Case 2: With expiration protection, check both policy and LDAP
        elif self.password_expiration_protection:
            policy_expiry = self.pass_last_mod_int + (self.password_age_days * int(self._DAY_FLOAT))
            if policy_expiry > self.current_time_int and self.expiration_time_attr > self.current_time_int:
                return False

        return True

    def _check_post_login_action(self):
        """
        Check if a post-login password change action should be performed.

        Returns:
            tuple: (bool: update needed, bool: perform post-action)
        """
        # Check if password was changed after last login
        if self._get_changed_password_hours_ago() < self.last_login_hours_ago:
            return False, False

        # Check if enough time has passed since login
        if self.last_login_hours_ago < self.post_authentication_reset_delay:
            return False, False

        # Check if action is configured
        if self.post_authentication_actions == self._ACTION_NONE:
            return False, False

        # Update needed, determine if post-action required
        return True, self.post_authentication_actions > self._ACTION_CHANGE_PASSWORD

    def _perform_post_action(self):
        """
        Perform post-password-change action based on configuration.
        """
        if self.post_authentication_actions == self._ACTION_TERMINATE_SESSIONS:
            self._terminate_user_sessions()
        elif self.post_authentication_actions == self._ACTION_REBOOT:
            log('D220')
            subprocess.run(["reboot"])

    def _terminate_user_sessions(self):
        """
        Terminates all processes associated with the active sessions of the target user.
        """
        # Get active sessions for the target user
        user_sessions = [user for user in psutil.users() if user.name == self.target_user]
        logdata = dict()
        logdata['target_user'] = self.target_user
        if not user_sessions:
            log('D227', logdata)
            return

        # Terminate each session
        for session in user_sessions:
            try:
                # Get the process and terminate it
                proc = psutil.Process(session.pid)
                proc.kill()  # Send SIGKILL
                logdata['pid'] = session.pid
                log('D228')
            except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
                logdata['pid'] = session.pid
                logdata['exc'] = exc
                log('W35', logdata)

    def update_laps_password(self):
        """
        Update the LAPS password if needed based on policy.
        Checks expiration and login times to determine if update is needed.
        """
        # Check if password update is needed
        update_needed, perform_post_action = self._should_update_password()

        if not update_needed:
            log('D229')
            return False

        # Generate new password
        password = self._generate_password()

        # Create encrypted password blob
        encrypted_blob = self._create_password_blob(password)

        # Update password in LDAP
        ldap_success = self._update_ldap_password(encrypted_blob)

        if not ldap_success:
            return False

        # Change local user password
        local_success = self._change_user_password(password)

        if not local_success:
            log('E76')
            return False

        log('D230')

        # Perform post-action if configured
        if perform_post_action:
            self._perform_post_action()


    def apply(self):
        """
        Main entry point for the LAPS applier.
        """
        if self.__module_enabled:
            log('D218')
            self.update_laps_password()
        else:
            log('D219')
