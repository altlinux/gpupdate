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
import distro

def getDistributiveVendor ():
    distr = list()
    try:
        distr=distro.linux_distribution(full_distribution_name=False)
    except:
        distr=('unknown','unknown','unknown')
    return distr


def is_rpm_installed(rpm_name):
    '''
    Check if the package named 'rpm_name' is installed
    '''
    ts = rpm.TransactionSet()
    pm = ts.dbMatch('name', rpm_name)

    if pm.count() > 0:
        return True

    return False

class Package:

    def __init__(self, package_name):
        distributive=getDistributiveVendor()
        if distributive[0]=="altlinux":
            self.__install_command = ['/usr/bin/apt-get', '-y', 'install']
            self.__remove_command = ['/usr/bin/apt-get', '-y', 'remove']
            self.__reinstall_command = ['/usr/bin/apt-get', '-y', 'reinstall']
        elif distributive[0]=="rosa":
            self.__install_command = ['/usr/bin/dnf', '-y', 'install']
            self.__remove_command = ['/usr/bin/dnf', '-y', 'remove']
            self.__reinstall_command = ['/usr/bin/dnf', '-y', 'reinstall']
        else:
            self.__install_command = ['/usr/bin/apt-get', '-y', 'install']
            self.__remove_command = ['/usr/bin/apt-get', '-y', 'remove']
            self.__reinstall_command = ['/usr/bin/apt-get', '-y', 'reinstall']
        self.package_name = package_name
        self.for_install = True

        if package_name.endswith('-'):
            self.package_name = package_name[:-1]
            self.for_install = False

        self.installed = is_rpm_installed(self.package_name)

    def mark_for_install(self):
        self.for_install = True

    def mark_for_removal(self):
        self.for_install = False

    def is_installed(self):
        return self.installed

    def is_for_install(self):
        return self.for_install

    def is_for_removal(self):
        return (not self.for_install)

    def action(self):
        if self.for_install:
            if not self.is_installed():
                return self.install()
        else:
            if self.is_installed():
                return self.remove()

    def install(self):
        fullcmd = self.__install_command
        fullcmd.append(self.package_name)
        return subprocess.check_call(fullcmd)

    def reinstall(self):
        fullcmd = self.__reinstall_command
        fullcmd.append(self.package_name)
        return subprocess.check_call(fullcmd)

    def remove(self):
        fullcmd = self.__remove_command
        fullcmd.append(self.package_name)
        return subprocess.check_call(fullcmd)

    def __repr__(self):
        return self.package_name

    def __str__(self):
        return self.package_name

def update():
    '''
    Update APT-RPM database.
    '''
    subprocess.check_call(['/usr/bin/apt-get', 'update'])

def install_rpm(rpm_name):
    '''
    Install single RPM
    '''
    rpm = Package(rpm_name)
    return rpm.install()

def remove_rpm(rpm_name):
    '''
    Remove single RPM
    '''
    rpm = Package(rpm_name)
    return rpm.remove()

def install_rpms(rpm_names):
    '''
    Install set of RPMs sequentially
    '''
    result = list()

    for package in rpm_names:
        result.append(install_rpm(package))

    return result

def remove_rpms(rpm_names):
    '''
    Remove set of RPMs requentially
    '''
    result = list()

    for package in rpm_names:
        result.append(remove_rpm(package))

    return result

