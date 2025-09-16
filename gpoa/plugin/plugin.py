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

from abc import ABC, abstractmethod
from gpoa.util.util import string_to_literal_eval
class plugin(ABC):
    def __init__(self, dict_dconf_db={}, username=None):
        self.dict_dconf_db = dict_dconf_db
        self.username = username

    def get_dict_registry(self, prefix=''):
        return  string_to_literal_eval(self.dict_dconf_db.get(prefix,{}))

    @abstractmethod
    def run(self):
        pass

