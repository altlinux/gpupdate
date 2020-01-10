#
# Copyright (C) 2019-2020 Igor Chudov
# Copyright (C) 2019-2020 Evgeny Sinelnikov
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

from .adp import adp
from .exceptions import PluginInitError
from util.logging import slogm

class plugin_manager:
    def __init__(self):
        self.plugins = dict()
        logging.info(slogm('Starting plugin manager'))
        try:
            self.plugins['adp'] = adp()
            logging.info(slogm('ADP plugin initialized'))
        except PluginInitError as exc:
            self.plugins['adp'] = None
            logging.error(slogm(exc))

    def run(self):
        if self.plugins['adp']:
            self.plugins['adp'].run()

