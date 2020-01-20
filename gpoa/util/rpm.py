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

import subprocess
import rpm


def is_rpm_installed(rpm_name):
    '''
    Check if the package named 'rpm_name' is installed
    '''
    ts = rpm.TransactionSet()
    pm = ts.dbMatch('name', rpm_name)

    if pm.count() > 0:
        return True

    return False


def update():
    '''
    Update APT-RPM database.
    '''
    subprocess.check_call(['/usr/bin/apt-get', 'update'])


def install_rpm(rpm_name):
    '''
    Install RPM from APT-RPM sources.
    '''
    update()
    subprocess.check_call(['/usr/bin/apt-get', '-y', 'install', rpm_name])


def remove_rpm(rpm_name):
    '''
    Remove RPM from file system.
    '''
    subprocess.check_call(['/usr/bin/apt-get', '-y', 'remove', rpm_name])

