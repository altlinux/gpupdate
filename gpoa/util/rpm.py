#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
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


def install_rpm(rpm_names, force=True):
    '''
    Install RPM from APT-RPM sources.

    :param rpm_names: List of names of RPM packages to install
    :param force: Check if RPM is installed
    '''

    install_command = ['/usr/bin/apt-get', '-y', 'install']

    update()
    if force:
        for package in rpm_names:
            if not is_rpm_installed(package)
                install_command.append(package)
    else:
        install_command.extend(rpm_names)

    subprocess.check_call(install_command)

def remove_rpm(rpm_names, force=True):
    '''
    Remove RPM from file system.

    :param rpm_names: List of names of RPM packages to install
    :param force: Check if rpm is installed
    '''
    remove_command = ['/usr/bin/apt-get', '-y', 'remove']

    update()

    if force:
        remove_command.extend(rpm_names)
    else:
        for package in rpm_names:
            if is_rpm_installed(package):
                remove_command.append(package)

    subprocess.check_call(remove_command)

