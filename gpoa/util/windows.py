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


import os
import pwd

from samba import getopt as options

from samba.gpclass import get_dc_hostname, check_refresh_gpo_list
from samba.netcmd.common import netcmd_get_domain_infos_via_cldap
import samba.gpo
import pysss_nss_idmap

from storage import cache_factory
from messages import message_with_code
from .xdg import (
      xdg_get_desktop
)
from .util import get_homedir
from .logging import log
from .samba import smbopts


class smbcreds (smbopts):

    def __init__(self, dc_fqdn=None):
        smbopts.__init__(self, 'GPO Applier')
        self.credopts = options.CredentialsOptions(self.parser)
        self.creds = self.credopts.get_credentials(self.lp, fallback_machine=True)
        self.set_dc(dc_fqdn)

    def get_dc(self):
        return self.selected_dc

    def set_dc(self, dc_fqdn):
        '''
        Force selection of the specified DC
        '''
        self.selected_dc = None

        try:
            if dc_fqdn is not None:
                logdata = dict()
                logdata['user_dc'] = dc_fqdn
                log('D38', logdata)

                self.selected_dc = dc_fqdn
            else:
                self.ls_selected_dc = set()
                self.selected_dc = get_dc_hostname(self.creds, self.lp)
                self.ls_selected_dc.add(self.selected_dc)
        except Exception as exc:
            logdata = dict()
            logdata['msg'] = str(exc)
            log('E10', logdata)
            raise exc

    def get_domain(self):
        '''
        Get current Active Directory domain name
        '''
        dns_domainname = None
        try:
            # Get CLDAP record about domain
            # Look and python/samba/netcmd/domain.py for more examples
            res = netcmd_get_domain_infos_via_cldap(self.lp, None, self.selected_dc)
            dns_domainname = res.dns_domain
            logdata = dict({'domain': dns_domainname})
            log('D18', logdata)
        except Exception as exc:
            log('E15')
            raise exc

        return dns_domainname

    def get_gpos(self, username):
        '''
        Get GPO list for the specified username for the specified DC
        hostname
        '''
        gpos = list()

        try:
            log('D48')
            ads = samba.gpo.ADS_STRUCT(self.selected_dc, self.lp, self.creds)
            if ads.connect():
                log('D47')
                gpos = ads.get_gpo_list(username)
                logdata = dict({'username': username})
                log('I1', logdata)
                for gpo in gpos:
                    # These setters are taken from libgpo/pygpo.c
                    # print(gpo.ds_path) # LDAP entry
                    ldata = dict({'gpo_name': gpo.display_name, 'gpo_uuid': gpo.name, 'file_sys_path': gpo.file_sys_path})
                    log('I2', ldata)

        except Exception as exc:
            logdata = dict({'username': username, 'dc': self.selected_dc})
            log('E17', logdata)

        return gpos

    def update_gpos(self, username):
        gpos = self.get_gpos(username)
        while self.ls_selected_dc:
            logdata = dict()
            logdata['username'] = username
            logdata['dc'] = self.selected_dc
            try:
                log('D49', logdata)
                check_refresh_gpo_list(self.selected_dc, self.lp, self.creds, gpos)
                log('D50', logdata)
                self.ls_selected_dc.clear()
            except Exception as exc:
                logdata['err'] = str(exc)
                self.selected_dc = get_dc_hostname(self.creds, self.lp)
                if self.selected_dc not in self.ls_selected_dc:
                    logdata['try'] = 'Search another dc'
                    log('F1', logdata)
                    self.ls_selected_dc.add(self.selected_dc)
                else:
                    log('F1', logdata)
                    raise exc
        return gpos

def wbinfo_getsid(domain, user):
    '''
    Get SID using wbinfo
    '''
    # This part works only on client
    username = '{}\\{}'.format(domain.upper(), user)
    sid = pysss_nss_idmap.getsidbyname(username)

    if username in sid:
        return sid[username]['sid']

    # This part works only on DC
    wbinfo_cmd = ['wbinfo', '-n', username]
    output = subprocess.check_output(wbinfo_cmd)
    sid = output.split()[0].decode('utf-8')

    return sid


def get_local_sid_prefix():
    return "S-1-5-21-0-0-0"


def get_sid(domain, username, is_machine = False):
    '''
    Lookup SID not only using wbinfo or sssd but also using own cache
    '''
    sid = 'local-{}'.format(username)

    # local user
    if not domain:
        found_uid = 0
        if not is_machine:
            found_uid = pwd.getpwnam(username).pw_uid
        return '{}-{}'.format(get_local_sid_prefix(), found_uid)

    # domain user
    try:
        sid = wbinfo_getsid(domain, username)
    except:
        logdata = dict({'sid': sid})
        log('E16', logdata)

    logdata = dict({'sid': sid})
    log('D21', logdata)

    return sid


def expand_windows_var(text, username=None):
    '''
    Scan the line for percent-encoded variables and expand them.
    '''
    variables = dict()
    variables['HOME'] = '/etc/skel'
    variables['SystemRoot'] = '/'
    variables['StartMenuDir'] = '/usr/share/applications'
    variables['SystemDrive'] = '/'
    variables['DesktopDir'] = xdg_get_desktop(username, variables['HOME'])

    if username:
        variables['LogonUser'] = username
        variables['HOME'] = get_homedir(username)

        variables['StartMenuDir'] = os.path.join(
            variables['HOME'], '.local', 'share', 'applications')

    result = text
    for var in variables.keys():
        result = result.replace('%{}%'.format(var), variables[var])

    return result


def transform_windows_path(text):
    '''
    Try to make Windows path look like UNIX.
    '''
    result = text

    if text.lower().endswith('.exe'):
        result = text.lower().replace('\\', '/').replace('.exe', '').rpartition('/')[2]

    return result

