#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2024 BaseALT Ltd.
# Copyright (C) 2024 Evgeny SInelnikov <sin@altlinux.org>.
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

__compat__ = False

from sqlalchemy import MetaData

try:
    from sqlalchemy.orm import registry
except:
    from sqlalchemy.orm import mapper
    __compat__ = True

class sqlite_registry_compat:
    def __init__(self, db_cnt):
        if not __compat__:
            self.__registry = registry()
            self.__metadata = MetaData()
        else:
            self.__metadata = MetaData(db_cnt)

    def metadata(self):
        return self.__metadata

    def map_imperatively(self, obj, table):
        if __compat__:
            mapper(obj, table)
        else:
            self.__registry.map_imperatively(obj, table)
