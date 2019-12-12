import logging

from xml.etree import ElementTree
from xdg.DesktopEntry import DesktopEntry

def read_shortcuts(shortcuts_file):
    '''
    Read shortcut objects from GPTs XML file
    '''
    shortcuts = list()
    xml_contents = ElementTree.parse(shortcuts_file)
    xml_root = xml_contents.getroot()

    for link in xml_root:
        props = link.find('Properties')
        path = props.get('targetPath')
        arguments = props.get('arguments')
        sc = shortcut(path, arguments, link.get('name'))
        sc.set_changed(link.get('changed'))
        sc.set_clsid(link.get('clsid'))
        sc.set_guid(link.get('uid'))
        sc.set_usercontext(link.get('userContext', False))
        shortcuts.append(sc)

    return shortcuts

def merge_shortcuts(username, sid):
    '''
    
    '''
    return None

class shortcut:
    def __init__(self, path, arguments, name=None):
        self.path = path
        self.arguments = arguments
        self.name = name
        self.changed = ''
        self.is_in_user_context = self.set_usercontext()

    def __str__(self):
        result = '<shortcut({} {} {})>'.format(
            self.path,
            self.arguments,
            self.name
        )
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

    def set_usercontext(self, context=False):
        '''
        Perform action in user context or not
        '''
        self.is_in_user_context = context

    def desktop(self, file_path=None):
        '''
        Returns desktop file object which may be written to disk.
        '''
        self.desktop_file = DesktopEntry()
        self.desktop_file.addGroup('Desktop Entry')
        self.desktop_file.set('Type', 'Application')
        self.desktop_file.set('Version', '1.0')
        self.desktop_file.set('Terminal', 'false')
        self.desktop_file.set('Exec', '{} {}'.format(self.path, self.arguments))
        self.desktop_file.set('Name', self.name)
        #desktop_file.write(file_path)

        return self.desktop_file
