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
import logging
from util.logging import slogm

class rpm:
    def __init__(self, packages_for_instsall, packages_for_remove):
        self.packages_for_instsall = packages_for_instsall
        self.packages_for_remove = packages_for_remove

    def apply(self):
        try:
            logging.info(slogm('Updating APT-RPM database'))
            subprocess.check_call(['/usr/bin/apt-get', 'update'])
        except Exception as exc:
            logging.info(slogm('Failed to update APT-RPM database: {}'.format(exc)))

        logging.info(slogm('Installing packages: {}. Removing packages {}.'.format(self.packages_for_instsall, self.packages_for_remove)))

        if self.packages_for_remove:
            self.packages_for_remove = [i + "-" for i in self.packages_for_remove]

        cmd = ['/usr/bin/apt-get', '-y', 'install']
        cmd.extend(self.packages_for_instsall)
        cmd.extend(self.packages_for_remove)

        try:
            subprocess.check_call(cmd)
        except Exception as exc:
            logging.info(slogm('Failed to install/remove packages: {}'.format(exc)))

