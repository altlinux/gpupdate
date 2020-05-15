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


import logging
import os
import pwd

from samba import getopt as options

from samba.gpclass import get_dc_hostname, check_refresh_gpo_list
from samba.netcmd.common import netcmd_get_domain_infos_via_cldap
import samba.gpo
import pysss_nss_idmap

from storage import cache_factory
from .xdg import get_user_dir
from .util import get_homedir
from .logging import slogm
from .samba import smbopts


class smbcreds (smbopts):

    def __init__(self, dc_fqdn=None):
        smbopts.__init__(self, 'GPO Applier')
        self.credopts = options.CredentialsOptions(self.parser)
        self.creds = self.credopts.get_credentials(self.lp, fallback_machine=True)
        self.selected_dc = self.set_dc(dc_fqdn)

    def get_dc(self):
        return self.selected_dc

    def set_dc(self, dc_fqdn):
        '''
        Force selection of the specified DC
        '''
        self.selected_dc = None

        try:
            samba_dc = get_dc_hostname(self.creds, self.lp)

            if samba_dc != dc_fqdn and dc_fqdn is not None:

                logging.debug(
                    slogm('Samba DC setting is {} and is overwritten by user setting {}'.format(
                        samba_dc, dc)))

                self.selected_dc = dc_fqdn
            else:
                self.selected_dc = samba_dc
        except Exception as exc:
            logging.error(slogm('Unable to determine DC hostname'))
            raise exc

        return self.selected_dc

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
            logging.info(slogm('Found domain via CLDAP: {}'.format(dns_domainname)))
        except Exception as exc:
            logging.error(slogm('Unable to retrieve domain name via CLDAP query'))
            raise exc

        return dns_domainname

    def get_gpos(self, username):
        '''
        Get GPO list for the specified username for the specified DC
        hostname
        '''
        gpos = list()

        try:
            ads = samba.gpo.ADS_STRUCT(self.selected_dc, self.lp, self.creds)
            if ads.connect():
                gpos = ads.get_gpo_list(username)
                logging.info(slogm('Got GPO list for {}:'.format(username)))
                for gpo in gpos:
                    # These setters are taken from libgpo/pygpo.c
                    # print(gpo.ds_path) # LDAP entry
                    logging.info(slogm('GPO: {} ({})'.format(gpo.display_name, gpo.name)))

        except Exception as exc:
            logging.error(
                slogm('Unable to get GPO list for {} from {}'.format(
                    username, self.selected_dc)))

        return gpos

    def update_gpos(self, username):
        gpos = self.get_gpos(username)

        try:
            check_refresh_gpo_list(self.selected_dc, self.lp, self.creds, gpos)
        except Exception as exc:
            logging.error(
                slogm('Unable to refresh GPO list for {} from {}'.format(
                    username, self.selected_dc)))
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
        logging.warning(
            slogm('Error getting SID using wbinfo, will use cached SID: {}'.format(sid)))

    logging.debug(slogm('Working with SID: {}'.format(sid)))

    return sid


def expand_windows_var(text, username=None):
    '''
    Scan the line for percent-encoded variables and expand them.
    '''
    variables = dict()
    variables['HOME'] = '/'
    variables['SystemRoot'] = '/'
    variables['StartMenuDir'] = '/usr/share/applications'
    variables['SystemDrive'] = '/'

    if username:
        variables['HOME'] = get_homedir(username)

        variables['DesktopDir'] = get_user_dir(
            'DESKTOP', os.path.join(variables['HOME'], 'Desktop'))

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

