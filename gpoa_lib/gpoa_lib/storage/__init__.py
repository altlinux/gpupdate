#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2023 BaseALT Ltd.
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


from .dconf_registry import Dconf_registry


def registry_factory(registry_name='', envprofile=None , username=None):
    if username:
        Dconf_registry._username = username
    else:
        Dconf_registry._envprofile = 'system'
    if envprofile:
        Dconf_registry._envprofile = envprofile

    if registry_name == 'dconf':
        return Dconf_registry()
    else:
        return Dconf_registry

