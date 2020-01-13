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

import logging
import subprocess

from util.rpm import is_rpm_installed
from .exceptions import PluginInitError
from util.logging import slogm

class adp:
    def __init__(self):
        if not is_rpm_installed('adp'):
            raise PluginInitError('adp is not installed - plugin cannot be initialized')
        logging.info(slogm('ADP plugin initialized'))

    def run(self):
        try:
            logging.info('Running ADP plugin')
            subprocess.call(['/usr/bin/adp', 'fetch'])
            subprocess.call(['/usr/bin/adp', 'apply'])
        except Exception as exc:
            logging.error(slogm('Error running ADP'))
            raise exc

