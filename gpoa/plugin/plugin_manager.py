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

import logging

from .adp import adp
from .roles import roles
from .exceptions import PluginInitError
from .plugin import plugin
from util.logging import slogm
from messages import message_with_code

class plugin_manager:
    def __init__(self):
        self.plugins = dict()
        logging.debug(slogm(message_with_code('D3')))
        try:
            self.plugins['adp'] = adp()
        except PluginInitError as exc:
            logging.warning(slogm(str(exc)))

    def run(self):
        self.plugins.get('adp', plugin('adp')).run()
        self.plugins.get('roles', plugin('roles')).run()

