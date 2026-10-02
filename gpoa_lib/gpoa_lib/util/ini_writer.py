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

import json

from .browser_policy import is_browser_json_value
from .logging import log


def _is_valid_dconf_segment(segment):
    """dconf/GVDB: segment must be non-empty and not start with '.'"""
    return bool(segment) and not segment.startswith('.')


def _is_valid_dconf_path(path):
    """No empty components (//). Each segment must be valid."""
    parts = [p for p in path.split('/') if p]
    return len(parts) > 0 and all(_is_valid_dconf_segment(p) for p in parts)


def write_ini_sections(file_obj, data):
    '''
    Write a nested dict as dconf INI sections to a file object.
    Invalid sections and keys are skipped with a warning.
    '''
    from ..storage.dconf_registry import encode_dconf_path, encode_dconf_segment
    for section, section_data in data.items():
        if not section:
            continue
        encoded_section = encode_dconf_path(section)
        if not _is_valid_dconf_path(encoded_section):
            log('W58', {'section': section})
            continue
        file_obj.write(f'[{encoded_section}]\n')
        if isinstance(section_data, dict):
            for key, value in section_data.items():
                if not key:
                    continue
                encoded_key = encode_dconf_segment(key)
                if not _is_valid_dconf_segment(encoded_key):
                    log('W59', {'section': section, 'key': key})
                    continue
                if isinstance(value, int):
                    file_obj.write(f'{encoded_key} = {value}\n')
                elif is_browser_json_value(section, value):
                    # Quote for GVariant, not by changing the JSON itself.
                    literal = json.dumps(value, ensure_ascii=False)
                    file_obj.write(f'{encoded_key} = {literal}\n')
                else:
                    file_obj.write(f'{encoded_key} = "{value}"\n')
        file_obj.write('\n')
