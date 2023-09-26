#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2022 BaseALT Ltd.
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

from util.xml import get_xml_root
from storage.dconf_registry import Dconf_registry

def read_inifiles(inifiles_file):
    inifiles = list()

    for ini in get_xml_root(inifiles_file):
        prors = ini.find('Properties')
        ini_obj = inifile(prors.get('path'))
        ini_obj.set_section(prors.get('section', default=None))
        ini_obj.set_property(prors.get('property', default=None))
        ini_obj.set_value(prors.get('value', default=None))
        ini_obj.set_action(prors.get('action'))

        inifiles.append(ini_obj)

    return inifiles

def merge_inifiles(storage, sid, inifile_objects, policy_name):
    for iniobj in inifile_objects:
        storage.add_ini(sid, iniobj, policy_name)

class inifile:
    def __init__(self, path):
        self.path = path

    def set_section(self, section):
        self.section = section
    def set_property(self, property):
        self.property = property
    def set_value(self, value):
        self.value = value
    def set_action(self, action):
        self.action = action

