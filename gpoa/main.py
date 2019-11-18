#! /usr/bin/env python3

import argparse

# Facility to determine GPTs for user
import optparse
from samba import getopt as options
from samba.gpclass import get_dc_hostname, gpo_version, check_safe_path
import samba.gpo

# Primitives to work with libregistry
# samba.registry.str_regtype(2) -> 'REG_EXPAND_SZ'
# Taken from python/samba/tests/registry.py
from samba import registry

# PReg object generator and parser
from samba.dcerpc import preg
from samba.dcerpc import misc
import samba.ndr
from samba.gp_parse.gp_pol import GPPolParser

# This is needed to query AD DOMAIN name from LDAP
# using cldap_netlogon (and to replace netads utility
# invocation helper).
from samba.dcerpc import netlogon
from samba.netcmd.common import netcmd_get_domain_infos_via_cldap

# Registry editing facilities are buggy. Use TDB module instead.
import tdb

# This is needed by Registry.pol file search
import os
import re
# This is needed for merging lists of PReg files.
import itertools

# This is needed for Username and SID caching
import pickle

# Our native control facility
import control

# This is needed by helper functions and must be removed after
# migration to native Python calls
import socket
import subprocess

# Facility to get SID from username
import pysss_nss_idmap

# Internal error
import sys


class tdb_regedit:
    '''
    regedit object for samba-regedit which has separate registry and
    not really related to registry formed in smb.conf.
    '''

    def __init__(self, tdb_file='/var/lib/samba/registry.tdb'):
        self.registry = tdb.open(tdb_file)

    def _blob2keys(self, blob):
        return blob.split('')

    def get_keys(self, path):
        # Keys are ending with trailing zeros and are binary blobs
        keys_blob = self.registry.get('{}\x00'.format(path).encode())
        return self._blob2keys

    def write_preg_entry(self, entry):
        hive_key = 'HKLM\\{}\\{}\\{}'.format(
                entry.keyname.upper(),
                entry.valuename,
                entry.type.to_bytes(1, byteorder='big')).upper().encode()
        print('Merging {}'.format(hive_key))

        self.registry.transaction_start()
        self.registry.store(hive_key, entry.data.to_bytes(4, byteorder='big'))
        self.registry.transaction_commit()

class applier_backend:
    def __init__(self):
        pass

def get_cache(cache_file, default_cache_obj):
    if not os.path.exists(cache_file):
        print('Initializing missing cache file: {}'.format(cache_file))
        with open(cache_file, 'wb') as f:
            pickle.dump(default_cache_obj, f, pickle.HIGHEST_PROTOCOL)

    data= None
    with open(cache_file, 'rb') as f:
        data = pickle.load(f)

    return data

class samba_backend(applier_backend):
    _samba_registry_file = '/var/cache/samba/registry.tdb'
    _mahine_hive = 'HKEY_LOCAL_MACHINE'
    _user_hive = 'HKEY_CURRENT_USER'
    _machine_pol_path_pattern = '[Mm][Aa][Cc][Hh][Ii][Nn][Ee]'
    _user_pol_path_pattern = '[Uu][Ss][Ee][Rr]'

    def _check_sysvol_present(self, gpo):
        '''
        Check if there is SYSVOL path for GPO assigned
        '''
        if not gpo.file_sys_path:
            print('No SYSVOL entry assigned to GPO {}'.format(gpo.name))
            return False
        return True

    def _gpo_get_gpt_polfiles(self, gpo_obj):
        '''
        Find absolute path to cached GPT directory and return
        dict of lists with PReg file paths.
        '''
        if self._check_sysvol_present(gpo_obj):
            print('Found SYSVOL entry {} for GPO {}'.format(gpo_obj.file_sys_path, gpo_obj.name))
            path = check_safe_path(gpo_obj.file_sys_path).upper()
            gpt_abspath = os.path.join(self.cache_dir, 'gpo_cache', path)
            print('Path: {}'.format(path))
            policy_files = self._find_regpol_files(gpt_abspath)

            return policy_files
        return dict({ 'machine_regpols': [], 'user_regpols': [] })

    def __init__(self, loadparm, creds, sid, dc, username):
        # Samba objects - LoadParm() and CredentialsOptions()
        self.loadparm = loadparm
        self.creds = creds

        self.cache_dir = self.loadparm.get('cache directory')
        print('Cache directory is: {}'.format(self.cache_dir))

        # Regular expressions to split PReg files into user and machine parts
        self._machine_pol_path_regex = re.compile(self._machine_pol_path_pattern)
        self._user_pol_path_regex = re.compile(self._user_pol_path_pattern)

        # User SID to work with HKCU hive
        self.username = username
        self.sid = sid

        # Look at python-samba tests for code examples
        self.registry = registry.Registry()
        self.machine_hive = registry.open_ldb(os.path.join(self.cache_dir, 'HKLM.ldb'))
        self.user_hive = registry.open_ldb(os.path.join(self.cache_dir, 'HKCU-{}.ldb'.format(self.sid)))
        self.registry.mount_hive(self.machine_hive, samba.registry.HKEY_LOCAL_MACHINE)
        self.registry.mount_hive(self.user_hive, samba.registry.HKEY_CURRENT_USER)

        self.policy_files = dict({ 'machine_regpols': [], 'user_regpols': [] })

        cache_file = os.path.join(self.cache_dir, 'cache.pkl')
        # Load PReg paths from cache at first
        cache = get_cache(cache_file, dict())

        try:
            gpos = get_gpo_list(dc, self.creds, self.loadparm, 'administrator')
            for gpo in gpos:
                polfiles = self._gpo_get_gpt_polfiles(gpo)
                self.policy_files['machine_regpols'] += polfiles['machine_regpols']
                self.policy_files['user_regpols']    += polfiles['user_regpols']
            # Cache paths to PReg files
            cache[sid] = self.policy_files
        except:
            print('Error fetching GPOs')
            if sid in cache:
                self.policy_files = cache[sid]
                print('Got cached PReg files')

        # Re-cache the retrieved values
        with open(cache_file, 'wb') as f:
            pickle.dump(cache, f, pickle.HIGHEST_PROTOCOL)
            print('Cached PReg files')

        print('Policy files: {}'.format(self.policy_files))

    def _parse_pol_file(self, polfile):
        '''
        Parse PReg file and return its preg object
        '''
        gpparser = GPPolParser()
        data = None

        with open(polfile, 'rb') as f:
            data = f.read()
            gpparser.parse(data)

        #print(gpparser.pol_file.__ndr_print__())
        return gpparser.pol_file

    def _merge_entry(self, hive, entry):
        '''
        Write preg.entry to hive
        '''
        # Build hive key path from PReg's key name and value name.
        hive_key = '{}\\{}'.format(entry.keyname, entry.valuename)
        print('Merging {}'.format(hive_key))

        # FIXME: Here should be entry.type parser in order to correctly
        # represent data
        hive.set_value(hive_key, entry.type, entry.data.to_bytes(4, byteorder='big'))
        hive.flush() # Dump data to disk

    def get_values(self):
        '''
        Read data from PReg file and return list of NDR objects (samba.preg)
        '''
        # FIXME: Return registry and hives instead of samba.preg objects.
        preg_objs = []
        print('Parsing machine regpols')

        for regpol in self.policy_files['machine_regpols']:
            print('Processing {}'.format(regpol))
            pregfile = self._parse_pol_file(regpol)
            preg_objs.append(pregfile)
            # Works only with full key names
            #self.registry.diff_apply(regpol)
            for entry in pregfile.entries:
                self._merge_entry(self.machine_hive, entry)

        return preg_objs

    def _find_regpol_files(self, gpt_path):
        '''
        Seek through given GPT directory absolute path and return the dictionary
        of user's and machine's Registry.pol files.
        '''
        print('Finding regpols in: {}'.format(gpt_path))
        polfiles = dict({ 'machine_regpols': [], 'user_regpols': [] })
        for root, dirs, files in os.walk(gpt_path):
            for gpt_file in files:
                if gpt_file.endswith('.pol'):
                    regpol_abspath = os.path.join(root, gpt_file)
                    if self._machine_pol_path_regex.search(regpol_abspath):
                        polfiles['machine_regpols'].append(regpol_abspath)
                    else:
                        polfiles['user_regpols'].append(regpol_abspath)
        print('Polfiles: {}'.format(polfiles))
        return polfiles



class applier_frontend:
    def __init__(self, regobj):
        pass

    def apply(self):
        pass

class control_applier(applier_frontend):
    _registry_branch = 'Software\\BaseALT\\Policies\\Control'

    def __init__(self, polfiles):
        self.polparsers = polfiles
        self.control_settings = self._get_controls(self.polparsers)
        self.controls = []
        for setting in self.control_settings:
            try:
                self.controls.append(control.control(setting.valuename, setting.data))
            except:
                print('Unable to work with control: {}'.format(setting.valuename))
        #for e in polfile.pol_file.entries:
        #    print('{}:{}:{}:{}:{}'.format(e.type, e.data, e.valuename, e.keyname))

    def _get_controls(self, polfiles):
        '''
        Extract control entries from PReg file
        '''
        controls = []
        for parser in polfiles:
            for entry in parser.entries:
                if entry.keyname == self._registry_branch:
                    controls.append(entry)
                    print('Found control setting: {}'.format(entry.valuename))
                else:
                    # Property names are taken from python/samba/gp_parse/gp_pol.py
                    print('Dropped control setting: {}\\{}'.format(entry.keyname, entry.valuename))
        return controls

    def apply(self):
        '''
        Trigger control facility invocation.
        '''
        for control in self.controls:
            control.set_control_status()

    def dump_settings(self):
        '''
        Write actual controls as XML and PReg files
        '''
        print('Dumping...')
        polfile = preg.file()
        polfile.header.signature = 'PReg'
        polfile.header.version = 1
        polfile.num_entries = len(self.control_settings)
        polfile.entries = self.control_settings
        print(polfile.__ndr_print__())
        
        policy_writer = GPPolParser()
        policy_writer.pol_file = polfile
        policy_writer.write_xml('test_reg.xml')
        policy_writer.write_binary('test_reg.pol')

class applier:
    def __init__(self, backend):
        self.backend = backend
        self.gpvalues = self.load_values()
        print('Values: {}'.format(self.gpvalues))
        capplier = control_applier(self.gpvalues)
        self.appliers = dict({ 'control': capplier })

    def load_values(self):
        '''
        This thing returns the list of samba.preg objects for
        now but it must be transformed to return registry and
        its hives to read values from.
        '''
        print('Get values from backend')
        return self.backend.get_values()

    def apply_parameters(self):
        print('Applying')
        self.appliers['control'].apply()
        # This thing dumps Registry.pol files to disk from data structures
        #print('Writing settings to file')
        #self.appliers['control'].dump_settings()

def parse_arguments():
    arguments = argparse.ArgumentParser(description='Generate configuration out of parsed policies')
    arguments.add_argument('user',
        type=str,
        default=get_machine_name(),
        help='Domain username ({}) to parse policies for'.format(get_machine_name()))
    arguments.add_argument('--dc',
        type=str,
        help='FQDN of the domain to replicate SYSVOL from')
    return arguments.parse_args()

def get_gpo_list(dc_hostname, creds, lp, user):
    gpos = []
    ads = samba.gpo.ADS_STRUCT(dc_hostname, lp, creds)
    if ads.connect():
        #gpos = ads.get_gpo_list(creds.get_username())
        gpos = ads.get_gpo_list(user)
    print('Got GPO list:')
    for gpo in gpos:
        # These setters are taken from libgpo/pygpo.c
        # print(gpo.ds_path) # LDAP entry
        print('{} ({})'.format(gpo.display_name, gpo.name))
    print('------')
    return gpos

def get_machine_domain():
    pass

def select_dc(lp, creds, dc):
    samba_dc = get_dc_hostname(creds, lp)

    if samba_dc != dc and dc != None:
        print('Samba DC setting is {} and is overwritten by user setting {}'.format(samba_dc, dc))
        return dc
    
    return samba_dc

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

def get_machine_name():
    '''
    Get localhost name looking like DC0$
    '''
    return socket.gethostname().split('.', 1)[0].upper() + "$"

def machine_kinit():
    '''
    Perform kinit with machine credentials
    '''
    host = get_machine_name()
    subprocess.call(['kinit', '-k', host])
    print('kinit succeed')

def check_krb_ticket():
    '''
    Check if Kerberos 5 ticket present
    '''
    try:
        subprocess.check_call([ 'klist', '-s' ])
        output = subprocess.check_output('klist', stderr=subprocess.STDOUT).decode()
        print(output)
    except:
        sys.exit( 1 )
    print('Ticket check succeed')

def get_domain_name(lp, creds, dc):
    '''
    Get current Active Directory domain name
    '''
    # Get CLDAP record about domain
    # Look and python/samba/netcmd/domain.py for more examples
    res = netcmd_get_domain_infos_via_cldap(lp, None, dc)
    print('Found domain via CLDAP: {}'.format(res.dns_domain))

    return res.dns_domain

def main():
    #back = hreg_filesystem_backend(args.sid)
    parser = optparse.OptionParser('GPO Applier')
    sambaopts = options.SambaOptions(parser)
    credopts = options.CredentialsOptions(parser)
    # Initialize loadparm context
    lp = sambaopts.get_loadparm()
    creds = credopts.get_credentials(lp, fallback_machine=True)

    sid_cache = os.path.join(lp.get('cache directory'), 'sid_cache.pkl')
    cached_sids = get_cache(sid_cache, dict())

    args = parse_arguments()

    machine_kinit()
    check_krb_ticket()

    # Determine the default Samba DC for replication and try
    # to overwrite it with user setting.
    dc = select_dc(lp, creds, args.dc)

    username = args.user
    domain = get_domain_name(lp, creds, dc)
    sid = ''

    domain_username = '{}\\{}'.format(domain, username)
    if domain_username in cached_sids:
        sid = cached_sids[domain_username]
        print('Got cached SID {} for user {}'.format(sid, domain_username))

    try:
        sid = wbinfo_getsid(domain, username)
    except:
        print('Error getting SID using wbinfo, will use cached SID: {}'.format(sid))

    print('Working with SID: {}'.format(sid))

    cached_sids[domain_username] = sid
    with open(sid_cache, 'wb') as f:
        pickle.dump(cached_sids, f, pickle.HIGHEST_PROTOCOL)
        print('Cached SID {} for user {}'.format(sid, domain_username))

    back = samba_backend(lp, creds, sid, dc, username)

    appl = applier(back)
    appl.apply_parameters()

if __name__ == "__main__":
    main()

