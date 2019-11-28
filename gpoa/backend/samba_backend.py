from .applier_backend import applier_backend

import argparse

# Facility to determine GPTs for user
import optparse
from samba import getopt as options
from samba.gpclass import check_safe_path

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
#from samba.dcerpc import netlogon

# This is needed by Registry.pol file search
import os
import re
# This is needed for merging lists of PReg files.
import itertools

# This is needed for Username and SID caching
import pickle

# Our native control facility
import util

# This is needed by helper functions and must be removed after
# migration to native Python calls
import socket
import subprocess

# Facility to get SID from username
import pysss_nss_idmap

# Internal error
import sys

# Remove print() from code
import logging
logging.basicConfig(level=logging.DEBUG)

class samba_backend(applier_backend):
    __default_policy_path = '/usr/lib/python3/site-packages/gpoa/local-policy/default.xml'
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
            logging.info('No SYSVOL entry assigned to GPO {}'.format(gpo.name))
            return False
        return True

    def _gpo_get_gpt_polfiles(self, gpo_obj):
        '''
        Find absolute path to cached GPT directory and return
        dict of lists with PReg file paths.
        '''
        if self._check_sysvol_present(gpo_obj):
            logging.debug('Found SYSVOL entry {} for GPO {}'.format(gpo_obj.file_sys_path, gpo_obj.name))
            path = check_safe_path(gpo_obj.file_sys_path).upper()
            gpt_abspath = os.path.join(self.cache_dir, 'gpo_cache', path)
            logging.debug('Path: {}'.format(path))
            policy_files = self._find_regpol_files(gpt_abspath)

            return policy_files
        return dict({ 'machine_regpols': [], 'user_regpols': [] })

    def __init__(self, loadparm, creds, sid, dc, username):
        # Samba objects - LoadParm() and CredentialsOptions()
        self.loadparm = loadparm
        self.creds = creds

        self.cache_dir = self.loadparm.get('cache directory')
        logging.debug('Cache directory is: {}'.format(self.cache_dir))

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

        self.policy_files = dict({ 'machine_regpols': [self.__default_policy_path], 'user_regpols': [] })

        cache_file = os.path.join(self.cache_dir, 'cache.pkl')
        # Load PReg paths from cache at first
        cache = util.get_cache(cache_file, dict())

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
                logging.info('Got cached PReg files')

        # Re-cache the retrieved values
        with open(cache_file, 'wb') as f:
            pickle.dump(cache, f, pickle.HIGHEST_PROTOCOL)
            logging.debug('Cached PReg files')

        logging.debug('Policy files: {}'.format(self.policy_files))

    def _merge_entry(self, hive, entry):
        '''
        Write preg.entry to hive
        '''
        # Build hive key path from PReg's key name and value name.
        hive_key = '{}\\{}'.format(entry.keyname, entry.valuename)
        logging.debug('Merging {}'.format(hive_key))

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
        logging.info('Parsing machine regpols')

        for regpol in self.policy_files['machine_regpols']:
            logging.debug('Processing {}'.format(regpol))
            pregfile = util.load_preg(regpol)
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
        logging.debug('Finding regpols in: {}'.format(gpt_path))
        polfiles = dict({ 'machine_regpols': [], 'user_regpols': [] })
        for root, dirs, files in os.walk(gpt_path):
            for gpt_file in files:
                if gpt_file.endswith('.pol'):
                    regpol_abspath = os.path.join(root, gpt_file)
                    if self._machine_pol_path_regex.search(regpol_abspath):
                        polfiles['machine_regpols'].append(regpol_abspath)
                    else:
                        polfiles['user_regpols'].append(regpol_abspath)
        logging.debug('Polfiles: {}'.format(polfiles))
        return polfiles

