#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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

import logging
import subprocess

from util.rpm import is_rpm_installed
from .exceptions import PluginInitError
from util.logging import slogm
from messages import message_with_code

class adp:
    def __init__(self):
        if not is_rpm_installed('adp'):
            raise PluginInitError(message_with_code('W5'))
        logging.info(slogm(message_with_code('D4')))

    def run(self):
        try:
            logging.info(slogm(message_with_code('D5')))
            subprocess.call(['/usr/bin/adp', 'fetch'])
            subprocess.call(['/usr/bin/adp', 'apply'])
        except Exception as exc:
            logging.error(slogm(message_with_code('E9')))
            raise exc

