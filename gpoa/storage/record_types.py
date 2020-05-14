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
    def __init__(self, preg_obj):
        self.hive_key = '{}\\{}'.format(preg_obj.keyname, preg_obj.valuename)
        self.type = preg_obj.type
        self.data = preg_obj.data

class samba_hkcu_preg(object):
    '''
    Object mapping representing HKCU entry (registry key with SID)
    '''
    def __init__(self, sid, preg_obj):
        self.sid = sid
        self.hive_key = '{}\\{}'.format(preg_obj.keyname, preg_obj.valuename)
        self.type = preg_obj.type
        self.data = preg_obj.data

class ad_shortcut(object):
    '''
    Object mapping representing Windows shortcut.
    '''
    def __init__(self, sid, sc):
        self.sid = sid
        self.path = sc.dest
        self.shortcut = sc.to_json()

class info_entry(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class printer_entry(object):
    '''
    Object mapping representing Windows printer of some type.
    '''
    def __init__(self, sid, pobj):
        self.sid = sid
        self.name = pobj.name
        self.printer = pobj.to_json()

class drive_entry(object):
    '''
    Object mapping representing Samba share bound to drive letter
    '''
    def __init__(self, sid, dobj):
        self.sid = sid
        self.login = dobj.login
        self.password = dobj.password
        self.dir = dobj.dir
        self.path = dobj.path

