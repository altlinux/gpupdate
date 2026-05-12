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


import os
import re
import tempfile
from functools import lru_cache
from typing import Optional

from samba.credentials import Credentials
from samba.net import Net
from samba.param import LoadParm

from .sid import get_sid
from .util import get_homedir, get_machine_name
from .xdg import xdg_get_desktop


class WindowsVarExpander:

    _PATTERN = re.compile(r'%([^%]+)%')

    _NON_PATH_VARS = {'LOGONUSER', 'USERNAME', 'COMPUTERNAME', 'DOMAINNAME',
                      'LDAPUSERSID', 'CURRENTPROCESSID'}

    @classmethod
    def clear_cache(cls) -> None:
        cls._build_map.cache_clear()
        xdg_get_desktop.cache_clear()

    @classmethod
    def expand(cls, text: str, username: Optional[str] = None) -> str:
        if '%' not in text:
            return text

        variables = cls._build_map(username)
        unknown = []

        def _replace(match: re.Match) -> str:
            key = match.group(1).upper()
            value = variables.get(key, match.group(0))
            if value == match.group(0):
                unknown.append(match.group(0))
            return value

        result = cls._PATTERN.sub(_replace, text)
        return result

    @classmethod
    @lru_cache(maxsize=32)
    def _build_map(cls, username: Optional[str] = None) -> dict[str, str]:
        if username:
            homedir      = get_homedir(username)
            start_menu   = os.path.join(homedir, '.local', 'share', 'applications')
            appdata      = os.path.join(homedir, '.config')
            localappdata = os.path.join(homedir, '.local', 'share')
        else:
            homedir      = '/etc/skel'
            start_menu   = '/usr/share/applications'
            appdata      = '/etc/skel'
            localappdata = '/etc/skel'

        desktop = xdg_get_desktop(username, homedir)
        tmp     = os.path.join(tempfile.gettempdir(), username) if username else tempfile.gettempdir()

        info   = get_kerberos_domain_info()
        pdc    = info.get('pdc_dns_name', '')
        domain = pdc.split('.', 1)[-1] if '.' in pdc else ''

        raw: dict[str, str] = {
            'HOME':              homedir,
            'HOMEPATH':          homedir,
            'HOMEDRIVE':         '/',
            'USERPROFILE':       homedir,
            'SYSTEMROOT':        '/',
            'SYSTEMDRIVE':       '/',
            'WINDIR':            '/',
            'DESKTOPDIR':        desktop,
            'STARTMENUDIR':      start_menu,
            'APPDATA':           appdata,
            'LOCALAPPDATA':      localappdata,
            'PROGRAMDATA':       '/var/lib',
            'PROGRAMFILES':      '/usr',
            'PROGRAMFILES(X86)': '/usr/lib',
            'PUBLIC':            '/usr/share',
            'TEMP':              tmp,
            'TMP':               tmp,
            'COMPUTERNAME':      get_machine_name(),
            'DOMAINNAME':        domain,
            'CURRENTPROCESSID':  str(os.getpid()),
        }

        if username:
            raw['LOGONUSER'] = username
            raw['USERNAME']  = username
            try:
                raw['LDAPUSERSID'] = get_sid(domain, username, is_machine=False)
            except Exception:
                pass

        result = {}
        for k, v in raw.items():
            if k in cls._NON_PATH_VARS or v.endswith('/'):
                result[k] = v
            else:
                result[k] = v + '/'

        return result


def expand_windows_var(text: str, username: Optional[str] = None) -> str:
    return WindowsVarExpander.expand(text, username)


def transform_windows_path(text):
    result = text

    if text.lower().endswith('.exe'):
        result = text.lower().replace('\\', '/').replace('.exe', '').rpartition('/')[2]

    return result

def get_kerberos_domain_info():
    try:
        creds = Credentials()
        creds.guess()
        lp = LoadParm()

        realm = creds.get_realm()

        net = Net(creds, lp, server=None)
        info = net.finddc(flags=0, domain=realm)

        return {
            "pdc_dns_name": info.pdc_dns_name,
            "principal": creds.get_principal(),
        }

    except Exception as exc:
        return {'Exception':exc}
