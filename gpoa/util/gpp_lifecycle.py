#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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

"""
Utility functions for GPP element identification and state management.
"""

import hashlib
from datetime import datetime


def generate_element_uid(element_type, **fields):
    '''
    Generate deterministic UID for GPP elements without native GUID.

    Uses SHA256 hash of key fields to create reproducible UID.

    :param element_type: Type of element ('inifile', 'file', 'folder', etc.)
    :param fields: Key fields that uniquely identify the element
    :return: GUID-formatted string

    Examples:
        >>> generate_element_uid('inifile', path='/tmp/test.ini',
        ...                      section='test', property='key')
        '{GENERATED-A1B2C3D4-E5F6-7890-ABCD-EF1234567890}'
    '''
    fields_string = '|'.join(str(v) for v in fields.values() if v is not None)
    uid_string = f'{element_type}|{fields_string}'

    hash_value = hashlib.sha256(uid_string.encode()).hexdigest()

    return '{{GENERATED-{}-{}-{}-{}-{}}}'.format(
        hash_value[0:8],
        hash_value[8:12],
        hash_value[12:16],
        hash_value[16:20],
        hash_value[20:32]
    )


def generate_ini_uid(element):
    '''
    Generate UID for Ini file element.

    :param element: inifile object
    :return: GUID string
    '''
    return generate_element_uid(
        'inifile',
        path=getattr(element, 'path', ''),
        section=getattr(element, 'section', ''),
        property=getattr(element, 'property', '')
    )


def generate_file_uid(element):
    '''
    Generate UID for File element.

    :param element: fileentry object
    :return: GUID string
    '''
    return generate_element_uid(
        'file',
        fromPath=getattr(element, 'fromPath', ''),
        targetPath=getattr(element, 'targetPath', '')
    )


def generate_folder_uid(element):
    '''
    Generate UID for Folder element.

    :param element: folderentry object
    :return: GUID string
    '''
    return generate_element_uid(
        'folder',
        path=getattr(element, 'path', ''),
        action=getattr(element, 'action', '')
    )


def generate_shortcut_uid(element):
    '''
    Generate UID for Shortcut element.

    :param element: shortcut object
    :return: GUID string
    '''
    return generate_element_uid(
        'shortcut',
        dest=getattr(element, 'dest', ''),
        path=getattr(element, 'path', '')
    )


def generate_drive_uid(element):
    '''
    Generate UID for Drive (mapped drive) element.

    :param element: drivemap object
    :return: GUID string
    '''
    return generate_element_uid(
        'drive',
        dir=getattr(element, 'dir', ''),
        path=getattr(element, 'path', '')
    )


def generate_envvar_uid(element):
    '''
    Generate UID for Environment Variable element.

    :param element: envvar object
    :return: GUID string
    '''
    return generate_element_uid(
        'envvar',
        name=getattr(element, 'name', '')
    )


def generate_networkshare_uid(element):
    '''
    Generate UID for Network Share element.

    :param element: networkshare object
    :return: GUID string
    '''
    return generate_element_uid(
        'networkshare',
        name=getattr(element, 'name', ''),
        path=getattr(element, 'path', '')
    )


def generate_printer_uid(element):
    '''
    Generate UID for Printer element.

    :param element: printer object
    :return: GUID string
    '''
    return generate_element_uid(
        'printer',
        name=getattr(element, 'name', ''),
        printer_type=getattr(element, 'printer_type', '')
    )


def generate_service_uid(element):
    '''
    Generate UID for Service element.

    :param element: service object
    :return: GUID string
    '''
    return generate_element_uid(
        'service',
        unit=getattr(element, 'unit', ''),
        servname=getattr(element, 'servname', '')
    )


# Mapping of element types to UID generators
UID_GENERATORS = {
    'inifile': generate_ini_uid,
    'fileentry': generate_file_uid,
    'folderentry': generate_folder_uid,
    'shortcut': generate_shortcut_uid,
    'drivemap': generate_drive_uid,
    'envvar': generate_envvar_uid,
    'networkshare': generate_networkshare_uid,
    'printer': generate_printer_uid,
    'service': generate_service_uid,
}


def get_or_generate_uid(element):
    '''
    Get existing UID or generate new one for element.

    :param element: GPP element object
    :return: GUID string (either existing or generated)
    '''
    if hasattr(element, 'uid') and element.uid:
        return element.uid

    class_name = element.__class__.__name__
    generator = UID_GENERATORS.get(class_name)

    if generator:
        return generator(element)

    return generate_element_uid(class_name)


def sanitize_for_json(value):
    '''
    Sanitize value for JSON storage in dconf.
    Convert special characters as needed.

    :param value: Any value to sanitize
    :return: Sanitized string
    '''
    if isinstance(value, str):
        return value.replace('"', '″').replace("'", '″')
    return value


def element_to_dict(element):
    '''
    Convert GPP element to dictionary for dconf storage.
    Includes all lifecycle-relevant attributes.

    :param element: GPP element object
    :return: Dictionary ready for JSON serialization
    '''
    result = dict(element.items()) if hasattr(element, 'items') else {}

    for key, value in element.__dict__.items():
        if not key.startswith('_'):
            result[key] = sanitize_for_json(value) if isinstance(value, str) else value

    return result
