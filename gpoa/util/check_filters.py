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

from gpoa.util.util import get_machine_name


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