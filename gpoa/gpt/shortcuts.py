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
from storage.dconf_registry import Dconf_registry

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

        sc = shortcut(dest, path, arguments, link.get('name'), props.get('action'), target_type)
        sc.set_changed(link.get('changed'))
        sc.set_clsid(link.get('clsid'))
        sc.set_guid(link.get('uid'))
        sc.set_usercontext(link.get('userContext', False))
        sc.set_icon(props.get('iconPath'))
        if props.get('comment'):
            sc.set_comment(props.get('comment'))

        shortcuts.append(sc)

    Dconf_registry.shortcuts.append(shortcuts)
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

    sc = shortcut(json_obj['dest'], json_obj['path'], json_obj['arguments'], json_obj['name'], json_obj['action'], link_type)
    sc.set_changed(json_obj['changed'])
    sc.set_clsid(json_obj['clsid'])
    sc.set_guid(json_obj['guid'])
    sc.set_usercontext(json_obj['is_in_user_context'])
    if 'comment' in json_obj:
        sc.set_comment(json_obj['comment'])
    if 'icon' in json_obj:
        sc.set_icon(json_obj['icon'])

    return sc

class shortcut:
    def __init__(self, dest, path, arguments, name=None, action=None, ttype=TargetType.FILESYSTEM):
        '''
        :param dest: Path to resulting file on file system
        :param path: Path where the link should point to
        :param arguments: Arguemnts to eecutable file
        :param name: Name of the application
        :param type: Link type - FILESYSTEM or URL
        '''
        self.dest = self.replace_slashes(dest)
        self.path = path
        self.expanded_path = None
        self.arguments = arguments
        self.name = self.replace_name(name)
        self.action = action
        self.changed = ''
        self.icon = None
        self.comment = ''
        self.is_in_user_context = self.set_usercontext()
        self.type = ttype

    def replace_slashes(self, input_path):
        if input_path.startswith('%'):
            index = input_path.find('%', 1)
            if index != -1:
                replace_path = input_path[:index + 2] + input_path[index + 2:].replace('/','-')
                return replace_path
        return input_path.replace('/','-')

    def replace_name(self, input_name):
        if input_name.startswith('%'):
            index = input_name.find('%', 1)
            if index != -1:
                replace_name = input_name[index + 2:]
                return replace_name
        return input_name

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

    def set_comment(self, comment):
        self.comment = comment

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
        content['action'] = self.action
        content['is_in_user_context'] = self.is_in_user_context
        content['type'] = ttype2str(self.type)
        if self.icon:
            content['icon'] = self.icon
        if self.comment:
            content['comment'] = self.comment
        result = self.desktop()
        result.content.update(content)

        return json.dumps(result.content)

    def desktop(self, dest=None):
        '''
        Returns desktop file object which may be written to disk.
        '''
        if dest:
            self.desktop_file = DesktopEntry(dest)
        else:
            self.desktop_file = DesktopEntry()
            self.desktop_file.addGroup('Desktop Entry')
            self.desktop_file.set('Version', '1.0')
        self._update_desktop()

        return self.desktop_file

    def _update_desktop(self):
        '''
        Update desktop file object from internal data.
        '''
        if self.type == TargetType.URL:
            self.desktop_file.set('Type', 'Link')
        else:
            self.desktop_file.set('Type', 'Application')

        self.desktop_file.set('Name', self.name)

        desktop_path = self.path
        if self.expanded_path:
            desktop_path = self.expanded_path
        if self.type == TargetType.URL:
            self.desktop_file.set('URL', desktop_path)
        else:
            self.desktop_file.set('Terminal', 'false')
            self.desktop_file.set('Exec', '{} {}'.format(desktop_path, self.arguments))
            self.desktop_file.set('Comment', self.comment)

        if self.icon:
            self.desktop_file.set('Icon', self.icon)

    def _write_desktop(self, dest, create_only=False, read_firstly=False):
        '''
        Write .desktop file to disk using path 'dest'. Please note that
        .desktop files must have executable bit set in order to work in
        GUI.
        '''
        sc = Path(dest)
        if sc.exists() and create_only:
            return

        if sc.exists() and read_firstly:
            self.desktop(dest).write(dest)
        else:
            self.desktop().write(dest)

        sc.chmod(sc.stat().st_mode | stat.S_IEXEC)

    def _remove_desktop(self, dest):
        '''
        Remove .desktop file fromo disk using path 'dest'.
        '''
        sc = Path(dest)
        if sc.exists():
            sc.unlink()

    def apply_desktop(self, dest):
        '''
        Apply .desktop file by action.
        '''
        if self.action == 'U':
            self._write_desktop(dest, read_firstly=True)
        elif self.action == 'D':
            self._remove_desktop(dest)
        elif self.action == 'R':
            self._remove_desktop(dest)
            self._write_desktop(dest)
        elif self.action == 'C':
            self._write_desktop(dest, create_only=True)
