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
import re
import tempfile
from functools import lru_cache
from typing import Optional
from pathlib import Path

from samba import NTSTATUSError
from samba.credentials import Credentials

try:
    from samba.gpclass import check_refresh_gpo_list, get_dc_hostname
except ImportError:
    from samba.gp.gpclass import get_dc_hostname, check_refresh_gpo_list, get_gpo_list

import ipaddress
import optparse
import random

import ldb
import netifaces
from samba.auth import system_session
import samba.gpo
from samba.net import Net
from samba.netcmd.common import netcmd_get_domain_infos_via_cldap
from samba.param import LoadParm
from samba.samdb import SamDB
from storage.dconf_registry import Dconf_registry, extract_display_name_version
from util.system import with_privileges

from gpoa.storage import registry_factory

from .exceptions import GetGPOListFail
from .logging import log
from .samba import smbopts
from .sid import get_sid
from .util import get_homedir, get_uid_by_username, get_machine_name
from .xdg import xdg_get_desktop


class smbcreds (smbopts):

    def __init__(self, dc_fqdn=None):
        smbopts.__init__(self, 'GPO Applier')

        self.creds = Credentials()
        self.creds.guess(self.lp)
        self.creds.set_machine_account()

        self.set_dc(dc_fqdn)
        self.sDomain = SiteDomainScanner(self.creds, self.lp, self.selected_dc)
        self.dc_site_servers = self.sDomain.select_site_servers()
        self.all_servers = self.sDomain.select_all_servers()
        [self.all_servers.remove(element)
        for element in self.dc_site_servers
        if element in self.all_servers]
        self.pdc_emulator_server = self.sDomain.select_pdc_emulator_server()

    def get_dc(self):
        return self.selected_dc

    def set_dc(self, dc_fqdn):
        '''
        Force selection of the specified DC
        '''
        self.selected_dc = None

        try:
            if dc_fqdn is not None:
                logdata = {}
                logdata['user_dc'] = dc_fqdn
                log('D38', logdata)

                self.selected_dc = dc_fqdn
            else:
                self.selected_dc = get_dc_hostname(self.creds, self.lp)
        except Exception as exc:
            logdata = {}
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
            logdata = {'domain': dns_domainname}
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
        gpos = []
        dconf_dict = self.get_dconf_dict(username)

        if not self.is_machine and Dconf_registry.get_info('trust'):
            dconf_dict_machine = self.get_dconf_dict()
            allow_trust_user_policy = dconf_dict_machine.get(
                'Software/BaseALT/Policies/GPUpdate', {}).get(
                    'AllowTrustUserPolicy', False)
            allow_trust_user_policy_win =  dconf_dict_machine.get(
                'Software\Policies\Microsoft\Windows\System', {}).get(
                    'AllowX-ForestPolicy-and-RUP', False)
            if allow_trust_user_policy or allow_trust_user_policy_win:
                try:
                    info = with_privileges(username, get_kerberos_domain_info)
                    pdc_dns_name = info.get('pdc_dns_name')
                    if pdc_dns_name:
                        Dconf_registry.set_info('pdc_dns_name', pdc_dns_name)
                        if '@' in username:
                            user_part, domain_part = username.rsplit('@', 1)
                            pdc_parts = pdc_dns_name.lower().split('.')
                            domain_parts = domain_part.lower().split('.')
                            if pdc_parts[-len(domain_parts):] == domain_parts:
                                username = user_part
                        gpos = get_gpo_list(pdc_dns_name, self.creds, self.lp, username)
                        logdata = {'username': username}
                        log('I12', logdata)
                        self.process_gpos(gpos, username, dconf_dict)
                        return gpos
                except Exception as exc:
                    return []

        try:
            log('D48')
            ads = samba.gpo.ADS_STRUCT(self.selected_dc, self.lp, self.creds)
            if ads.connect():
                log('D47')
                gpos = ads.get_gpo_list(username)
                logdata = {'username': username}
                log('I1', logdata)
                self.process_gpos(gpos, username, dconf_dict)

        except Exception as exc:
            if self.selected_dc != self.pdc_emulator_server:
                raise GetGPOListFail(exc)
            logdata = {'username': username, 'dc': self.selected_dc, 'exc': exc}
            log('E17', logdata)

        return gpos

    def get_dconf_dict(self, username=None):
        """
        Retrieve dconf dictionary either for the machine itself
        or for a specific user depending on the given username
        """
        if username is None:
            return Dconf_registry.get_dictionary_from_dconf_file_db(save_dconf_db=True)
        elif Dconf_registry.get_info('machine_name') == username:
            dconf_dict = Dconf_registry.get_dictionary_from_dconf_file_db(save_dconf_db=True)
            self.is_machine = True
        else:
            dconf_dict = Dconf_registry.get_dictionary_from_dconf_file_db(get_uid_by_username(username), save_dconf_db=True)
            self.is_machine = False
        return dconf_dict


    def process_gpos(self, gpos, username, dconf_dict):
        """
        Process GPO objects and update their file_sys_path if cached version is valid
        """
        dict_gpo_name_version = extract_display_name_version(dconf_dict, username)
        for gpo in gpos:
            # These setters are taken from libgpo/pygpo.c
            cached_info = dict_gpo_name_version.get(gpo.display_name, {})

            # Check if GPO version matches and cached path exists
            if cached_info.get('version') == str(getattr(gpo, 'version', None)):
                if Path(cached_info.get('correct_path', '')).exists():
                    gpo.file_sys_path = ''
                    logdata = {
                        'gpo_name': gpo.display_name,
                        'gpo_uuid': gpo.name,
                        'file_sys_path_cache': True
                    }
                    log('I11', logdata)
                    continue
            # Default log if no cache hit
            logdata = {
                'gpo_name': gpo.display_name,
                'gpo_uuid': gpo.name,
                'file_sys_path': gpo.file_sys_path
            }
            log('I2', logdata)

    def update_gpos(self, username):

        list_selected_dc = set()



        if self.dc_site_servers:
            self.selected_dc = self.dc_site_servers.pop()

        self.all_servers = [dc for dc in self.all_servers if dc != self.selected_dc]
        list_selected_dc.add(self.selected_dc)

        try:
            gpos = self.get_gpos(username)

        except GetGPOListFail:
            self.selected_dc = self.pdc_emulator_server
            gpos = self.get_gpos(username)

        while list_selected_dc:
            logdata = {}
            logdata['username'] = username
            logdata['dc'] = self.selected_dc
            try:
                log('D49', logdata)
                if not self.is_machine and Dconf_registry.get_info('trust'):
                    check_refresh_gpo_list(Dconf_registry.get_info('pdc_dns_name'),
                                           self.lp,
                                           self.creds,
                                           gpos)
                else:
                    check_refresh_gpo_list(self.selected_dc, self.lp, self.creds, gpos)
                log('D50', logdata)
                list_selected_dc.clear()
            except NTSTATUSError as smb_exc:
                logdata['smb_exc'] = str(smb_exc)
                if not check_scroll_enabled():
                    if self.pdc_emulator_server and self.selected_dc != self.pdc_emulator_server:
                        self.selected_dc = self.pdc_emulator_server
                        logdata['action'] = 'Selected pdc'
                        logdata['pdc'] = self.selected_dc
                        log('W11', logdata)
                    else:
                        log('F1', logdata)
                        raise smb_exc
                else:
                    if self.dc_site_servers:
                        self.selected_dc = self.dc_site_servers.pop()
                    elif self.all_servers:
                        self.selected_dc = self.all_servers.pop()
                    else:
                        self.selected_dc = self.pdc_emulator_server


                    if self.selected_dc not in list_selected_dc:
                        logdata['action'] = 'Search another dc'
                        logdata['another_dc'] = self.selected_dc
                        log('W11', logdata)
                        list_selected_dc.add(self.selected_dc)
                    else:
                        log('F1', logdata)
                        raise smb_exc
            except Exception as exc:
                logdata['exc'] = str(exc)
                log('F1', logdata)
                raise exc
        return gpos


class SiteDomainScanner:
    def __init__(self, smbcreds, lp, dc):
        self.samdb = SamDB(url='ldap://{}'.format(dc), session_info=system_session(), credentials=smbcreds, lp=lp)
        Dconf_registry.set_info('samdb', self.samdb)
        self.pdc_emulator = self._search_pdc_emulator()

    @staticmethod
    def _get_ldb_single_message_attr(ldb_message, attr_name, encoding='utf8'):
        if attr_name in ldb_message:
            return ldb_message[attr_name][0].decode(encoding)
        else:
            return None

    @staticmethod
    def _get_ldb_single_result_attr(ldb_result, attr_name, encoding='utf8'):
        if len(ldb_result) == 1 and attr_name in ldb_result[0]:
            return ldb_result[0][attr_name][0].decode(encoding)
        else:
            return None

    def _get_server_hostname(self, ds_service_name):
        ds_service_name_dn = ldb.Dn(self.samdb, ds_service_name)
        server_dn = ds_service_name_dn.parent()
        res = self.samdb.search(server_dn, scope=ldb.SCOPE_BASE)
        return self._get_ldb_single_result_attr(res, 'dNSHostName')

    def _search_pdc_emulator(self):
        res = self.samdb.search(self.samdb.domain_dn(), scope=ldb.SCOPE_BASE)
        pdc_settings_object = self._get_ldb_single_result_attr(res, 'fSMORoleOwner')
        return self._get_server_hostname(pdc_settings_object)

    def get_ip_addresses(self):
        interface_list = netifaces.interfaces()
        addresses = []
        for iface in interface_list:
            address_entry = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in address_entry:
                addresses.extend(ipaddress.ip_address(ipv4_address_entry['addr']) for ipv4_address_entry in address_entry[netifaces.AF_INET])
            if netifaces.AF_INET6 in address_entry:
                addresses.extend(ipaddress.ip_address(ipv6_address_entry['addr']) for ipv6_address_entry in address_entry[netifaces.AF_INET6])
        return addresses

    def get_ad_subnets_sites(self):
        subnet_dn = ldb.Dn(self.samdb, "CN=Subnets,CN=Sites")
        config_dn = self.samdb.get_config_basedn()
        subnet_dn.add_base(config_dn)
        res = self.samdb.search(subnet_dn, ldb.SCOPE_ONELEVEL, expression='objectClass=subnet', attrs=['cn', 'siteObject'])
        subnets = {ipaddress.ip_network(self._get_ldb_single_message_attr(msg, 'cn')): self._get_ldb_single_message_attr(msg, 'siteObject') for msg in res}
        return subnets

    def get_ad_site_servers(self, site):
        servers_dn = ldb.Dn(self.samdb, "CN=Servers")
        site_dn = ldb.Dn(self.samdb, site)
        servers_dn.add_base(site_dn)
        res = self.samdb.search(servers_dn, ldb.SCOPE_ONELEVEL, expression='objectClass=server', attrs=['dNSHostName'])
        servers = [self._get_ldb_single_message_attr(msg, 'dNSHostName') for msg in res]
        random.shuffle(servers)
        return servers

    def get_ad_all_servers(self):
        sites_dn = ldb.Dn(self.samdb, "CN=Sites")
        config_dn = self.samdb.get_config_basedn()
        sites_dn.add_base(config_dn)
        res = self.samdb.search(sites_dn, ldb.SCOPE_SUBTREE, expression='objectClass=server', attrs=['dNSHostName'])
        servers = [self._get_ldb_single_message_attr(msg, 'dNSHostName') for msg in res]
        random.shuffle(servers)
        return servers

    def check_ip_in_subnets(self, ip_addresses, subnets_sites):
        return next((subnets_sites[subnet] for subnet in subnets_sites.keys()
                     if any(ip_address in subnet for ip_address in ip_addresses)), None)

    def select_site_servers(self):
        try:
            ip_addresses = self.get_ip_addresses()
            subnets_sites = self.get_ad_subnets_sites()

            our_site = self.check_ip_in_subnets(ip_addresses, subnets_sites)

            servers = []
            if our_site:
                servers = self.get_ad_site_servers(our_site)
            random.shuffle(servers)
            return servers
        except Exception as e:
            return []

    def select_all_servers(self):
        try:
            servers = self.get_ad_all_servers()
            random.shuffle(servers)
            return servers
        except Exception as e:
            return []

    def select_pdc_emulator_server(self):
        return self.pdc_emulator

class WindowsVarExpander:
    """
    Expand percent-encoded Windows variables (%HOME%, %AppData%, …) to
    POSIX paths.

    Design notes
    ------------
    - Single-pass regex substitution: O(n) instead of O(n·m).
    - Case-insensitive lookup: %home% == %HOME% == %Home%.
    - Per-username variable map is built once and cached (lru_cache).
    - xdg_get_desktop() result is also cached — no repeated os.popen calls.
    - Unknown variables are left unchanged (no silent corruption).
    """

    # Matches any %TOKEN% where TOKEN contains no percent signs
    _PATTERN = re.compile(r'%([^%]+)%')

    # Variables that hold non-path values — trailing slash must NOT be added
    _NON_PATH_VARS = {'LOGONUSER', 'USERNAME', 'COMPUTERNAME', 'DOMAINNAME',
                      'LDAPUSERSID', 'CURRENTPROCESSID'}

    @classmethod
    def clear_cache(cls) -> None:
        """Invalidate all cached variable maps (useful in tests)."""
        cls._build_map.cache_clear()
        xdg_get_desktop.cache_clear()

    @classmethod
    def expand(cls, text: str, username: Optional[str] = None) -> str:
        """
        Expand Windows-style variables in *text*.

        :param text:     Input string, e.g. ``'%HOME%/docs'``.
        :param username: When given, user-specific paths are used;
                         otherwise system-wide defaults apply.
        :returns:        Expanded string; unknown tokens are preserved.
        """
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
        """
        Build and cache the UPPER-CASE variable map for *username*.
        All values are normalised to end with '/'.
        """
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
    '''
    Scan the line for percent-encoded variables and expand them.
    '''
    return WindowsVarExpander.expand(text, username)


def transform_windows_path(text):
    '''
    Try to make Windows path look like UNIX.
    '''
    result = text

    if text.lower().endswith('.exe'):
        result = text.lower().replace('\\', '/').replace('.exe', '').rpartition('/')[2]

    return result

def check_scroll_enabled():
    storage = registry_factory()
    enable_scroll = '/Software/BaseALT/Policies/GPUpdate/ScrollSysvolDC'
    if storage.get_key_value(enable_scroll):
        data = storage.get_hklm_entry(enable_scroll).data
        return bool(int(data))
    else:
        return False

def get_kerberos_domain_info():
    """
    Retrieve information about the AD domain using Kerberos tickets
    """
    try:
        # Initialize credentials and load Samba parameters
        creds = Credentials()
        creds.guess()
        lp = LoadParm()

        # Get current realm
        realm = creds.get_realm()

        # Query domain controller
        net = Net(creds, lp, server=None)
        info = net.finddc(flags=0, domain=realm)

        return {
            "pdc_dns_name": info.pdc_dns_name,
            "principal": creds.get_principal(),
        }

    except Exception as exc:
        return {'Exception':exc}