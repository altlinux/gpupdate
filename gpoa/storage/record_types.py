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

class samba_preg(object):
    '''
    Object mapping representing HKLM entry (registry key without SID)
    '''
    def __init__(self, preg_obj, policy_name):
        self.policy_name = policy_name
        self.keyname = preg_obj.keyname
        self.valuename = preg_obj.valuename
        self.hive_key = '{}\\{}'.format(self.keyname, self.valuename)
        self.type = preg_obj.type
        self.data = preg_obj.data

    def update_fields(self):
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['type'] = self.type
        fields['data'] = self.data

        return fields

class samba_hkcu_preg(object):
    '''
    Object mapping representing HKCU entry (registry key with SID)
    '''
    def __init__(self, sid, preg_obj, policy_name):
        self.sid = sid
        self.policy_name = policy_name
        self.keyname = preg_obj.keyname
        self.valuename = preg_obj.valuename
        self.hive_key = '{}\\{}'.format(self.keyname, self.valuename)
        self.type = preg_obj.type
        self.data = preg_obj.data

    def update_fields(self):
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['type'] = self.type
        fields['data'] = self.data

        return fields

class ad_shortcut(object):
    '''
    Object mapping representing Windows shortcut.
    '''
    def __init__(self, sid, sc, policy_name):
        self.sid = sid
        self.policy_name = policy_name
        self.path = sc.dest
        self.shortcut = sc.to_json()

    def update_fields(self):
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['path'] = self.path
        fields['shortcut'] = self.shortcut

        return fields

class info_entry(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def update_fields(self):
        fields = dict()
        fields['value'] = self.value

        return fields

class printer_entry(object):
    '''
    Object mapping representing Windows printer of some type.
    '''
    def __init__(self, sid, pobj, policy_name):
        self.sid = sid
        self.policy_name = policy_name
        self.name = pobj.name
        self.printer = pobj.to_json()

    def update_fields(self):
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['name'] = self.name
        fields['printer'] = self.printer.to_json()

        return fields

class drive_entry(object):
    '''
    Object mapping representing Samba share bound to drive letter
    '''
    def __init__(self, sid, dobj, policy_name):
        self.sid = sid
        self.policy_name = policy_name
        self.login = dobj.login
        self.password = dobj.password
        self.dir = dobj.dir
        self.path = dobj.path

    def update_fields(self):
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['login'] = self.login
        fields['password'] = self.password
        fields['dir'] = self.dir
        fields['path'] = self.path

        return fields

class folder_entry(object):
    '''
    Object mapping representing file system directory
    '''
    def __init__(self, sid, fobj, policy_name):
        self.sid = sid
        self.policy_name = policy_name
        self.path = fobj.path
        self.action = fobj.action.value
        self.delete_folder = str(fobj.delete_folder)
        self.delete_sub_folders = str(fobj.delete_sub_folders)
        self.delete_files = str(fobj.delete_files)

    def update_fields(self):
        '''
        Return list of fields to update
        '''
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['action'] = self.action
        fields['delete_folder'] = self.delete_folder
        fields['delete_sub_folders'] = self.delete_sub_folders
        fields['delete_files'] = self.delete_files

        return fields

class envvar_entry(object):
    '''
    Object mapping representing environment variables
    '''
    def __init__(self, sid, evobj, policy_name):
        self.sid = sid
        self.policy_name = policy_name
        self.name = evobj.name
        self.value = evobj.value
        self.action = evobj.action.value

    def update_fields(self):
        '''
        Return list of fields to update
        '''
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['action'] = self.action
        fields['value'] = self.value

        return fields

class script_entry(object):
    '''
    Object mapping representing scripts.ini
    '''
    def __init__(self, sid, scrobj, policy_name):
        self.sid = sid
        self.policy_name = policy_name
        self.action = scrobj.action
        self.number = scrobj.number
        self.path = scrobj.path
        self.arg = scrobj.args

    def update_fields(self):
        '''
        Return list of fields to update
        '''
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['action'] = self.action
        fields['number'] = self.number
        fields['path'] = self.path
        fields['arg'] = self.arg

        return fields

class file_entry(object):
    '''
    Object mapping representing FILES.XML
    '''
    def __init__(self, sid, scrobj, policy_name):
        self.sid = sid
        self.policy_name = policy_name
        self.action = scrobj.action
        self.fromPath = scrobj.fromPath
        self.targetPath = scrobj.targetPath
        self.readOnly = scrobj.readOnly
        self.archive = scrobj.archive
        self.hidden = scrobj.hidden
        self.suppress = scrobj.suppress


    def update_fields(self):
        '''
        Return list of fields to update
        '''
        fields = dict()
        fields['policy_name'] = self.policy_name
        fields['action'] = self.action
        fields['fromPath'] = self.fromPath
        fields['targetPath'] = self.targetPath
        fields['readOnly'] = self.readOnly
        fields['archive'] = self.archive
        fields['hidden'] = self.hidden
        fields['suppress'] = self.suppress

        return fields
