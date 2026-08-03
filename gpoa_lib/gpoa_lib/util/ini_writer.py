#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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


def write_ini_sections(file_obj, data):
    '''
    Write a nested dict as dconf INI sections to a file object.
    '''
    from ..storage.dconf_registry import encode_dconf_path, encode_dconf_segment
    for section, section_data in data.items():
        if not section:
            continue
        file_obj.write(f'[{encode_dconf_path(section)}]\n')
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                if not key:
                    continue
                encoded_key = encode_dconf_segment(key)
                if isinstance(value, int):
                    file_obj.write(f'{encoded_key} = {value}\n')
                else:
                    file_obj.write(f'{encoded_key} = "{value}"\n')
        file_obj.write('\n')
