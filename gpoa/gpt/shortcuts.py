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

from pathlib import Path
import stat
import logging
from enum import Enum

from xml.etree import ElementTree
from xdg.DesktopEntry import DesktopEntry
import json

from util.windows import transform_windows_path
from util.xml import get_xml_root

class TargetType(Enum):
    FILESYSTEM = 'FILESYSTEM'
    URL = 'URL'

def get_ttype(targetstr):
    '''
    Validation function for targetType property

    :targetstr: String representing link type.

    :returns: Object of type TargetType.
    '''
    ttype = TargetType.FILESYSTEM

    if targetstr == 'URL':
        ttype = TargetType.URL

    return ttype

def ttype2str(ttype):
    '''
    Transform TargetType to string for JSON serialization

    :param ttype: TargetType object
    '''
    result = 'FILESYSTEM'

    if ttype == TargetType.URL:
        result = 'URL'

    return result

def read_shortcuts(shortcuts_file):
    '''
    Read shortcut objects from GPTs XML file

    :shortcuts_file: Location of Shortcuts.xml
    '''
    shortcuts = list()

    for link in get_xml_root(shortcuts_file):
        props = link.find('Properties')
        # Location of the link itself
        dest = props.get('shortcutPath')
        # Location where link should follow
        path = transform_windows_path(props.get('targetPath'))
        # Arguments to executable file
        arguments = props.get('arguments')
        # URL or FILESYSTEM
        target_type = get_ttype(props.get('targetType'))

        sc = shortcut(dest, path, arguments, link.get('name'), target_type)
        sc.set_changed(link.get('changed'))
        sc.set_clsid(link.get('clsid'))
        sc.set_guid(link.get('uid'))
        sc.set_usercontext(link.get('userContext', False))
        sc.set_icon(props.get('iconPath'))
        shortcuts.append(sc)

    return shortcuts

def merge_shortcuts(storage, sid, shortcut_objects, policy_name):
    for shortcut in shortcut_objects:
        storage.add_shortcut(sid, shortcut, policy_name)

def json2sc(json_str):
    '''
    Build shortcut out of string-serialized JSON
    '''
    json_obj = json.loads(json_str)
    link_type = get_ttype(json_obj['type'])

    sc = shortcut(json_obj['dest'], json_obj['path'], json_obj['arguments'], json_obj['name'], link_type)
    sc.set_changed(json_obj['changed'])
    sc.set_clsid(json_obj['clsid'])
    sc.set_guid(json_obj['guid'])
    sc.set_usercontext(json_obj['is_in_user_context'])
    if 'icon' in json_obj:
        sc.set_icon(json_obj['icon'])

    return sc

class shortcut:
    def __init__(self, dest, path, arguments, name=None, ttype=TargetType.FILESYSTEM):
        '''
        :param dest: Path to resulting file on file system
        :param path: Path where the link should point to
        :param arguments: Arguemnts to eecutable file
        :param name: Name of the application
        :param type: Link type - FILESYSTEM or URL
        '''
        self.dest = dest
        self.path = path
        self.expanded_path = None
        self.arguments = arguments
        self.name = name
        self.changed = ''
        self.icon = None
        self.is_in_user_context = self.set_usercontext()
        self.type = ttype

    def __str__(self):
        result = self.to_json()
        return result

    def set_changed(self, change_date):
        '''
        Set object change date
        '''
        self.changed = change_date

    def set_clsid(self, clsid):
        self.clsid = clsid

    def set_guid(self, uid):
        self.guid = uid

    def set_icon(self, icon_name):
        self.icon = icon_name

    def set_type(self, ttype):
        '''
        Set type of the hyperlink - FILESYSTEM or URL

        :ttype: - object of class TargetType
        '''
        self.type = ttype

    def set_usercontext(self, usercontext=False):
        '''
        Perform action in user context or not
        '''
        ctx = False

        if usercontext in [1, '1', True]:
            ctx = True

        self.is_in_user_context = ctx

    def set_expanded_path(self, path):
        '''
        Adjust shortcut path with expanding windows variables
        '''
        self.expanded_path = path

    def is_usercontext(self):
        return self.is_in_user_context

    def to_json(self):
        '''
        Return shortcut's JSON for further serialization.
        '''
        content = dict()
        content['dest'] = self.dest
        content['path'] = self.path
        content['name'] = self.name
        content['arguments'] = self.arguments
        content['clsid'] = self.clsid
        content['guid'] = self.guid
        content['changed'] = self.changed
        content['is_in_user_context'] = self.is_in_user_context
        content['type'] = ttype2str(self.type)
        if self.icon:
            content['icon'] = self.icon
        result = self.desktop()
        result.content.update(content)

        return json.dumps(result.content)

    def desktop(self):
        '''
        Returns desktop file object which may be written to disk.
        '''
        self.desktop_file = DesktopEntry()
        self.desktop_file.addGroup('Desktop Entry')

        if self.type == TargetType.URL:
            self.desktop_file.set('Type', 'Link')
        else:
            self.desktop_file.set('Type', 'Application')

        self.desktop_file.set('Version', '1.0')
        self.desktop_file.set('Name', self.name)

        desktop_path = self.path
        if self.expanded_path:
            desktop_path = self.expanded_path
        if self.type == TargetType.URL:
            self.desktop_file.set('URL', desktop_path)
        else:
            self.desktop_file.set('Terminal', 'false')
            self.desktop_file.set('Exec', '{} {}'.format(desktop_path, self.arguments))

        if self.icon:
            self.desktop_file.set('Icon', self.icon)

        return self.desktop_file

    def write_desktop(self, dest):
        '''
        Write .desktop file to disk using path 'dest'. Please note that
        .desktop files must have executable bit set in order to work in
        GUI.
        '''
        self.desktop().write(dest)
        sc = Path(dest)
        sc.chmod(sc.stat().st_mode | stat.S_IEXEC)

