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

import json
from base64 import b64decode
from Crypto.Cipher import AES

from util.xml import get_xml_root

def read_drives(drives_file):
    drives = list()

    for drive in get_xml_root(drives_file):
        drive_obj = drivemap()

        props = drive.find('Properties')
        drive_obj.set_login(props.get('username'))
        drive_obj.set_pass(props.get('cpassword'))

        drives.append(drive_obj)

    return drives

def decrypt_pass(cpassword):
    '''
    AES key for cpassword decryption: http://msdn.microsoft.com/en-us/library/2c15cbf0-f086-4c74-8b70-1f2fa45dd4be%28v=PROT.13%29#endNote2
    '''
    key = (
            b'\x4e\x99\x06\xe8'
            b'\xfc\xb6\x6c\xc9'
            b'\xfa\xf4\x93\x10'
            b'\x62\x0f\xfe\xe8'
            b'\xf4\x96\xe8\x06'
            b'\xcc\x05\x79\x90'
            b'\x20\x9b\x09\xa4'
            b'\x33\xb6\x6c\x1b'
    )
    cpass_len = len(cpassword)
    padded_pass = (cpassword + "=" * ((4 - cpass_len % 4) % 4))
    password = b64decode(padded_pass)
    decrypter = AES(key, AES.MODE_CBC, '\x00' * 16)

    return decrypter.decrypt(password)

class drivemap:
    def __init__(self):
        self.login = None
        self.password = None

    def set_login(self, username):
        self.login = username

    def set_pass(self, password):
        self.password = password

    def to_json(self):
        drive = dict()

        contents = dict()
        contents['drive'] = drive

        return json.dumps(contents)

