#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

"""Filter checking utilities for GPOA."""

import socket
import datetime
import os
import threading
from pathlib import Path

from util.logging import log
from util.util import get_machine_name
from util.users import get_process_user, is_root, get_local_groups_for_username
from util.sid import get_sid, get_group_sids_for_sid


class UserContext:
    MACHINE = '0'
    USER = '1'


def _is_user_context(value):
    return value in (UserContext.USER, 1, True)


def _extract_name_without_domain(name):
    if '\\' in name:
        _, name_part = name.split('\\', 1)
        return name_part
    return name


def _get_group_sids_for_subject(domain, subject_name, is_user):
    if not domain:
        return []
    try:
        subject_sid = get_sid(domain, subject_name, is_machine=not is_user)
        return get_group_sids_for_sid(subject_sid)
    except Exception as exc:
        log('W55', {'domain': domain, 'subject': subject_name, 'exc': str(exc)})
        return []


class FilterChecker:
    """Filter evaluation with caching for GPO targeting preferences."""

    _lock = threading.Lock()
    _domain_cache = {}
    _groups_cache = {}
    _machine_name_cache = None
    _fqdn_cache = None
    _user_environ_cache = {}
    FILTER_HANDLERS = None

    @classmethod
    def _get_handlers(cls):
        if cls.FILTER_HANDLERS is None:
            cls.FILTER_HANDLERS = {
                'FilterComputer': cls.check_computer,
                'FilterDomain': cls.check_domain,
                'FilterDate': cls.check_date,
                'FilterUser': cls.check_user,
                'FilterGroup': cls.check_group,
                'FilterVariable': cls.check_variable,
                'FilterTime': cls.check_time,
                'FilterCpu': cls.check_cpu,
                'FilterBattery': cls.check_battery,
            }
        return cls.FILTER_HANDLERS

    @staticmethod
    def check_computer(filter_obj, username=None):
        expected_name = getattr(filter_obj, 'name', '')
        if not expected_name:
            return True

        filter_type = getattr(filter_obj, 'type', 'NETBIOS').upper()

        try:
            if filter_type == 'DNS':
                actual_name = FilterChecker._resolve_fqdn().lower()
            else:
                actual_name = FilterChecker._resolve_machine_name().rstrip('$').lower()

            if actual_name is None:
                actual_name = ''
        except Exception:
            actual_name = ''

        expected_normalized = expected_name.lower().rstrip('$')
        return expected_normalized == actual_name

    @staticmethod
    def check_domain(filter_obj, username=None):
        expected_domain = getattr(filter_obj, 'name', '')
        if not expected_domain:
            return True

        user_context = getattr(filter_obj, 'userContext', UserContext.MACHINE)
        actual_domain = FilterChecker._get_domain_for_context(user_context, username)
        return actual_domain.lower() == expected_domain.lower()

    @staticmethod
    def check_date(filter_obj, username=None):
        period = getattr(filter_obj, 'period', '').upper()
        if not period:
            return True

        today = datetime.date.today()
        result = False

        dow_map = {
            'SUN': 0, 'MON': 1, 'TUE': 2, 'WED': 3,
            'THU': 4, 'FRI': 5, 'SAT': 6
        }

        if period == 'WEEKLY':
            dow_str = getattr(filter_obj, 'dow', '').upper()
            if dow_str in dow_map:
                current_dow = (today.weekday() + 1) % 7
                result = (current_dow == dow_map[dow_str])
            else:
                result = False

        elif period == 'MONTHLY':
            day_str = getattr(filter_obj, 'day', '')
            try:
                day = int(day_str)
                result = (today.day == day)
            except ValueError:
                result = False

        elif period == 'YEARLY':
            day_str = getattr(filter_obj, 'day', '')
            month_str = getattr(filter_obj, 'month', '')
            year_str = getattr(filter_obj, 'year', '')
            try:
                day = int(day_str)
                month = int(month_str)
                if day <= 0 or month <= 0 or month > 12:
                    result = False
                else:
                    if year_str:
                        year = int(year_str)
                        result = (today.year == year and today.month == month and today.day == day)
                    else:
                        result = (today.month == month and today.day == day)
            except ValueError:
                result = False

        else:
            log('W53', {'period': period})
            return True

        return result

    @staticmethod
    def check_user(filter_obj, username=None):
        if username is None:
            username = FilterChecker._resolve_process_user()

        sid = getattr(filter_obj, 'sid', '')
        if sid:
            domain = FilterChecker._get_domain_for_context(UserContext.USER, username)
            current_sid = get_sid(domain, username)
            return current_sid == sid

        filter_name = getattr(filter_obj, 'name', '')
        if not filter_name:
            return True

        filter_user = _extract_name_without_domain(filter_name)
        return filter_user.lower() == username.lower()

    @staticmethod
    def check_group(filter_obj, username=None):
        filter_sid = getattr(filter_obj, 'sid', '')
        filter_name = getattr(filter_obj, 'name', '')
        user_context = getattr(filter_obj, 'userContext', UserContext.MACHINE)

        is_user_ctx = _is_user_context(user_context)

        if filter_sid:
            domain = FilterChecker._get_domain_for_context(user_context, username)

            if is_user_ctx:
                if username is None:
                    username = FilterChecker._resolve_process_user()
                subject_name = username
            else:
                subject_name = FilterChecker._resolve_machine_name()

            if domain:
                group_sids = _get_group_sids_for_subject(domain, subject_name, is_user_ctx)
                return filter_sid in group_sids
            return False
        else:
            if is_user_ctx:
                if username is None:
                    username = FilterChecker._resolve_process_user()

                local_groups = FilterChecker._resolve_local_groups(username)
                group_name = _extract_name_without_domain(filter_name)

                return group_name in local_groups
            return False

    @staticmethod
    def check_variable(filter_obj, username=None):
        variable_name = getattr(filter_obj, 'variableName', '')
        expected_value = getattr(filter_obj, 'value', '')
        if not variable_name:
            return True

        if username:
            actual_value = FilterChecker._get_user_environ(username).get(variable_name, '')
        else:
            actual_value = os.environ.get(variable_name, '')

        return actual_value == expected_value

    @staticmethod
    def check_time(filter_obj, username=None):
        begin_str = getattr(filter_obj, 'begin', '')
        end_str = getattr(filter_obj, 'end', '')
        if not begin_str or not end_str:
            return True

        begin = datetime.time.fromisoformat(begin_str)
        end = datetime.time.fromisoformat(end_str)
        now = datetime.datetime.now().time()

        if begin <= end:
            return begin <= now <= end
        else:
            return now >= begin or now <= end

    @staticmethod
    def check_cpu(filter_obj, username=None):
        speed_mhz = getattr(filter_obj, 'speedMHz', '')
        if not speed_mhz:
            return True
        expected = int(speed_mhz)

        actual = 0
        try:
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if line.startswith('cpu MHz'):
                        val = int(float(line.split(':')[1].strip()))
                        if val > actual:
                            actual = val
        except (OSError, ValueError):
            pass

        return actual >= expected

    @staticmethod
    def check_battery(filter_obj, username=None):
        try:
            for entry in Path('/sys/class/power_supply').iterdir():
                if entry.name.startswith('BAT'):
                    return True
        except OSError:
            pass
        return False

    @classmethod
    def _get_user_environ(cls, username):
        if username in cls._user_environ_cache:
            return cls._user_environ_cache[username]

        with cls._lock:
            if username in cls._user_environ_cache:
                return cls._user_environ_cache[username]
            env = cls._read_all_user_environ(username)
            cls._user_environ_cache[username] = env
            return env

    @staticmethod
    def _read_all_user_environ(username):
        target = f'USER={username}'.encode()
        result = {}
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit():
                continue
            try:
                with open(str(entry / 'environ'), 'rb') as f:
                    raw = f.read()
            except (OSError, PermissionError):
                continue
            if target in raw.split(b'\0'):
                for item in raw.split(b'\0'):
                    if b'=' in item:
                        k, v = item.split(b'=', 1)
                        key = k.decode()
                        val = v.decode()
                        result[key] = val
        return result

    @classmethod
    def reset_cache(cls):
        """Clear all caches. Call between GPO processing sessions."""
        with cls._lock:
            cls._domain_cache.clear()
            cls._groups_cache.clear()
            cls._machine_name_cache = None
            cls._fqdn_cache = None
            cls._user_environ_cache.clear()

    @classmethod
    def _resolve_fqdn(cls):
        return cls._get_fqdn()

    @classmethod
    def _resolve_process_user(cls):
        return get_process_user()

    @classmethod
    def _resolve_machine_name(cls):
        return cls._get_machine_name_cached()

    @classmethod
    def _resolve_local_groups(cls, username):
        return cls._get_cached_local_groups(username)

    @classmethod
    def _get_domain_for_context(cls, user_context, username=None):
        cache_key = (str(user_context), username or '')
        if cache_key in cls._domain_cache:
            return cls._domain_cache[cache_key]

        with cls._lock:
            if cache_key in cls._domain_cache:
                return cls._domain_cache[cache_key]

            from util.windows import smbcreds, get_kerberos_domain_info
            from util.system import with_privileges

            result = ''
            is_uc = _is_user_context(user_context)
            try:
                if is_uc:
                    uname = username or get_process_user()
                    if is_root():
                        info = with_privileges(uname, get_kerberos_domain_info)
                    else:
                        info = get_kerberos_domain_info()
                    if 'Exception' not in info:
                        principal = info.get('principal', '')
                        if '@' in principal:
                            result = principal.split('@')[1]
                else:
                    domain = smbcreds().get_domain()
                    if domain is not None:
                        result = domain
            except Exception as exc:
                log('W54', {'user_context': str(user_context), 'username': username or '', 'exc': str(exc)})

            cls._domain_cache[cache_key] = result
            return result

    @classmethod
    def _get_cached_local_groups(cls, username):
        if username in cls._groups_cache:
            return cls._groups_cache[username]

        with cls._lock:
            if username in cls._groups_cache:
                return cls._groups_cache[username]
            cls._groups_cache[username] = get_local_groups_for_username(username)
            return cls._groups_cache[username]

    @classmethod
    def _get_machine_name_cached(cls):
        if cls._machine_name_cache is None:
            with cls._lock:
                if cls._machine_name_cache is None:
                    cls._machine_name_cache = get_machine_name()
        return cls._machine_name_cache

    @classmethod
    def _get_fqdn(cls):
        if cls._fqdn_cache is None:
            with cls._lock:
                if cls._fqdn_cache is None:
                    cls._fqdn_cache = socket.getfqdn()
        return cls._fqdn_cache