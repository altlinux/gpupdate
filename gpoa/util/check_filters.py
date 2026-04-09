#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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

from gpoa.util.logging import log
from gpoa.util.util import get_machine_name
from gpoa.util.users import get_process_user, is_root, get_local_groups_for_username
from gpoa.util.sid import get_sid, get_group_sids_for_sid


def _get_domain_for_context(user_context, username=None):
    """Get domain for given context (user or computer).
    
    Args:
        user_context: '1', 1, True for user context, '0', 0, False for computer
        username: Target username for user context (optional)
    
    Returns:
        str: Domain name or empty string if not available
    """
    from gpoa.util.windows import smbcreds, get_kerberos_domain_info
    from gpoa.util.system import with_privileges
    
    is_user_context = user_context in [1, '1', True]
    
    try:
        if is_user_context:
            # User context - get domain from Kerberos ticket
            if username is None:
                username = get_process_user()
            
            # Get domain for the user (with privileges if root)
            if is_root():
                info = with_privileges(username, get_kerberos_domain_info)
            else:
                info = get_kerberos_domain_info()
            
            if 'Exception' not in info:
                principal = info.get('principal', '')
                if '@' in principal:
                    return principal.split('@')[1]
        else:
            # Computer context - get computer's domain
            domain_checker = smbcreds()
            domain = domain_checker.get_domain()
            if domain is not None:
                return domain
    except Exception:
        pass
    
    return ''


def _extract_name_without_domain(name):
    """Extract name part without domain prefix.
    
    Args:
        name: Name possibly with domain prefix (DOMAIN\\name)
    
    Returns:
        str: Name without domain part
    """
    if '\\' in name:
        _, name_part = name.split('\\', 1)
        return name_part
    return name


def _get_group_sids_for_subject(domain, subject_name, is_user):
    """Get group SIDs for a subject (user or computer).
    
    Args:
        domain: Domain name
        subject_name: Username or computer name
        is_user: True for user, False for computer
    
    Returns:
        list: List of group SIDs
    """
    from gpoa.util.sid import get_sid, get_group_sids_for_sid
    
    if not domain:
        return []
    
    try:
        subject_sid = get_sid(domain, subject_name, is_machine=not is_user)
        return get_group_sids_for_sid(subject_sid)
    except Exception:
        return []


def check_filter_computer(filter_obj, username=None):
    """Check if current computer name matches filter.

    Args:
        filter_obj (Filter): Filter object with attributes like 'name', 'type'
        username (str, optional): Target username (unused for computer filter)

    Returns:
        bool: True if computer name matches filter
    """
    expected_name = getattr(filter_obj, 'name', '')
    if not expected_name:
        return True

    filter_type = getattr(filter_obj, 'type', 'NETBIOS').upper()

    try:
        if filter_type == 'DNS':
            actual_name = socket.getfqdn().lower()
        else:
            actual_name = get_machine_name().rstrip('$').lower()

        if actual_name is None:
            actual_name = ''
    except Exception:
        actual_name = ''

    expected_normalized = expected_name.lower().rstrip('$')
    result = expected_normalized == actual_name

    return result


def check_filter_domain(filter_obj, username=None):
    """Check if current domain or user domain matches filter.

    Args:
        filter_obj (Filter): Filter object with attributes 'name', 'userContext'
        username (str, optional): Target username (unused for domain filter)

    Returns:
        bool: True if domain matches filter
    """
    expected_domain = getattr(filter_obj, 'name', '')
    if not expected_domain:
        return True

    user_context = getattr(filter_obj, 'userContext', '0')
    
    actual_domain = _get_domain_for_context(user_context, username)
    
    result = (actual_domain.lower() == expected_domain.lower())

    return result


def check_filter_date(filter_obj, username=None):
    """Check if current date matches filter.

    Args:
        filter_obj (Filter): Filter object with attributes 'period', 'dow', 'day', 'month', 'year', 'negate'
        username (str, optional): Target username (unused for date filter)

    Returns:
        bool: True if date matches filter
    """
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


