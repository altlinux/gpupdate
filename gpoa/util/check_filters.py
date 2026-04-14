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

"""Filter checking utilities for GPOA."""

import socket
import datetime

from gpoa.util.logging import log
from gpoa.util.util import get_machine_name
from gpoa.util.users import get_process_user, is_root, get_local_groups_for_username
from gpoa.util.sid import get_sid, get_group_sids_for_sid


def _is_user_context(value):
    return value in (1, '1', True)


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
    except Exception:
        return []


class FilterChecker:
    """Filter evaluation with caching for GPO targeting preferences."""

    _domain_cache = {}
    _groups_cache = {}
    _machine_name_cache = None
    _fqdn_cache = None

    FILTER_HANDLERS = {}

    @staticmethod
    def check_computer(filter_obj, username=None):
        expected_name = getattr(filter_obj, 'name', '')
        if not expected_name:
            return True

        filter_type = getattr(filter_obj, 'type', 'NETBIOS').upper()

        try:
            if filter_type == 'DNS':
                actual_name = FilterChecker._get_fqdn().lower()
            else:
                actual_name = FilterChecker._get_machine_name_cached().rstrip('$').lower()

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

        user_context = getattr(filter_obj, 'userContext', '0')
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
            return True

        return result

    @staticmethod
    def check_user(filter_obj, username=None):
        if username is None:
            username = get_process_user()

        sid = getattr(filter_obj, 'sid', '')
        if sid:
            domain = FilterChecker._get_domain_for_context('1', username)
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
        user_context = getattr(filter_obj, 'userContext', '0')

        is_user_ctx = _is_user_context(user_context)

        if filter_sid:
            domain = FilterChecker._get_domain_for_context(user_context, username)

            if is_user_ctx:
                if username is None:
                    username = get_process_user()
                subject_name = username
            else:
                subject_name = get_machine_name()

            if domain:
                group_sids = _get_group_sids_for_subject(domain, subject_name, is_user_ctx)
                return filter_sid in group_sids
            return False
        else:
            if is_user_ctx:
                if username is None:
                    username = get_process_user()

                local_groups = FilterChecker._get_cached_local_groups(username)
                group_name = _extract_name_without_domain(filter_name)

                return group_name in local_groups
            return False

    @classmethod
    def reset_cache(cls):
        """Clear all caches. Call between GPO processing sessions."""
        cls._domain_cache.clear()
        cls._groups_cache.clear()
        cls._machine_name_cache = None
        cls._fqdn_cache = None

    @classmethod
    def _get_domain_for_context(cls, user_context, username=None):
        cache_key = (str(user_context), username or '')
        if cache_key in cls._domain_cache:
            return cls._domain_cache[cache_key]

        from gpoa.util.windows import smbcreds, get_kerberos_domain_info
        from gpoa.util.system import with_privileges

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
        except Exception:
            pass

        cls._domain_cache[cache_key] = result
        return result

    @classmethod
    def _get_cached_local_groups(cls, username):
        if username not in cls._groups_cache:
            cls._groups_cache[username] = get_local_groups_for_username(username)
        return cls._groups_cache[username]

    @classmethod
    def _get_machine_name_cached(cls):
        if cls._machine_name_cache is None:
            cls._machine_name_cache = get_machine_name()
        return cls._machine_name_cache

    @classmethod
    def _get_fqdn(cls):
        if cls._fqdn_cache is None:
            cls._fqdn_cache = socket.getfqdn()
        return cls._fqdn_cache


FilterChecker.FILTER_HANDLERS = {
    'FilterComputer': FilterChecker.check_computer,
    'FilterDomain': FilterChecker.check_domain,
    'FilterDate': FilterChecker.check_date,
    'FilterUser': FilterChecker.check_user,
    'FilterGroup': FilterChecker.check_group,
}