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
        cmd = 'update\n'
        cmd += 'install ' + self.packages_for_instsall + '\n'
        cmd += 'remove ' + self.packages_for_remove + '\n'
        cmd += 'commit -y\n'

        try:
            logging.info(slogm('Installing packages: {}. Removing packages: {}.'.format(self.packages_for_instsall, self.packages_for_remove)))
            p = subprocess.run(['/usr/bin/apt-shell'], stdout = subprocess.PIPE, stderr = subprocess.PIPE, input = cmd, encoding='utf-8')
        except Exception as exc:
            logging.error(slogm('Failed to run /usr/bin/apt-shell: {}'.format(exc)))
            return

        logging.info(slogm('/usr/bin/apt-shell returned {}'.format(p.returncode)))
        logging.info(slogm('/usr/bin/apt-shell output:\n{}'.format(p.stdout)))
        if p.stderr:
            logging.error(slogm('/usr/bin/apt-shell errors:\n{}'.format(p.stderr)))

