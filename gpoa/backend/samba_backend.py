from .applier_backend import applier_backend

import argparse

# Facility to determine GPTs for user
import optparse
from samba import getopt as options
from samba.gpclass import check_safe_path, check_refresh_gpo_list

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

from collections import OrderedDict

# Remove print() from code
import logging
logging.basicConfig(level=logging.DEBUG)

class samba_backend(applier_backend):
    __default_policy_path = '/usr/share/local-policy/default'
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

    def _get_pol(self, username):
        '''
        Get PReg file paths from GPTs for specified username.
        '''
        policy_files = OrderedDict({ 'machine_regpols': [], 'user_regpols': [] })

        try:
            gpos = util.get_gpo_list(self.dc, self.creds, self.loadparm, username)

            # GPT replication function
            try:
                check_refresh_gpo_list(self.dc, self.loadparm, self.creds, gpos)
            except:
                logging.error('Unable to replicate GPTs from {} for {}'.format(self.dc, username))

            for gpo in gpos:
                polfiles = self._gpo_get_gpt_polfiles(gpo)
                policy_files['machine_regpols'] += polfiles['machine_regpols']
                policy_files['user_regpols']    += polfiles['user_regpols']
            # Cache paths to PReg files
            self.cache[self.sid] = policy_files
        except:
            logging.error('Error fetching GPO list from {} for'.format(self.dc, username))
            if self.sid in self.cache:
                policy_files = self.cache[sid]
                logging.info('Got cached PReg files')

        return policy_files

    def __init__(self, loadparm, creds, sid, dc, username):
        self.machine_entries = OrderedDict()
        self.user_entries = OrderedDict()

        self.user_machine_entries = OrderedDict()
        self.user_user_entries = OrderedDict()

        # Check if we're working for user or for machine
        self._is_machine_username = False
        if util.get_machine_name() == username:
            self._is_machine_username = True

        # Samba objects - LoadParm() and CredentialsOptions()
        self.loadparm = loadparm
        self.creds = creds
        self.dc = dc

        self.cache_dir = self.loadparm.get('cache directory')
        logging.debug('Cache directory is: {}'.format(self.cache_dir))

        # Regular expressions to split PReg files into user and machine parts
        self._machine_pol_path_regex = re.compile(self._machine_pol_path_pattern)
        self._user_pol_path_regex = re.compile(self._user_pol_path_pattern)

        # User SID to work with HKCU hive
        self.username = username
        self.sid = sid

        cache_file = os.path.join(self.cache_dir, 'cache.pkl')
        # Load PReg paths from cache at first
        self.cache = util.get_cache(cache_file, OrderedDict())

        # Get policies for machine at first.
        self.policy_files = self._get_pol(self.username)
        self.policy_files['machine_regpols'].insert(0, os.path.join(self.__default_policy_path, 'local.xml'))
        self.machine_entries = self._get_values(self.policy_files['machine_regpols'], self.machine_entries)
        self.user_entries = self._get_values(self.policy_files['user_regpols'], self.user_entries)

        self.user_policy_files = None
        # Load user GPT values in case user's name specified
        if not self._is_machine_username:
            self.user_policy_files = self._get_pol(self.username)
            self.user_machine_entries = self._get_values(self.user_policy_files['machine_regpols'], self.user_machine_entries)
            self.user_user_entries = self._get_values(self.user_policy_files['user_regpols'], self.user_user_entries)
            for entry in self.user_machine_entries:
                self._merge_entry(self.machine_entries, entry)
            for entry in self.user_user_entries:
                self._merge_entry(self.user_entries, entry)


        # Re-cache the retrieved values
        util.dump_cache(cache_file, self.cache)

        logging.debug('Policy files: {}'.format(self.policy_files))

    def _merge_entry(self, hive, entry):
        '''
        Write preg.entry to hive
        '''
        # Build hive key path from PReg's key name and value name.
        hive_key = '{}\\{}'.format(entry.keyname, entry.valuename)
        logging.debug('Merging {}'.format(hive_key))
        hive[hive_key] = entry

    def get_values(self):
        '''
        Read data from PReg file and return list of NDR objects (samba.preg)
        '''
        # FIXME: Return registry and hives instead of samba.preg objects.
        return self.machine_entries

    def get_user_values(self):
        return self.user_entries

    def _get_values(self, policy_files, hive_obj):
        for regpol in policy_files:
            try:
                logging.debug('Processing {}'.format(regpol))
                pregfile = util.load_preg(regpol)
                # Works only with full key names
                for entry in pregfile.entries:
                    self._merge_entry(hive_obj, entry)
            except:
                logging.error('Error processing {}'.format(regpol))

        return list(hive_obj.values())

    def _find_regpol_files(self, gpt_path):
        '''
        Seek through given GPT directory absolute path and return the dictionary
        of user's and machine's Registry.pol files.
        '''
        logging.debug('Finding regpols in: {}'.format(gpt_path))

        polfiles = dict({ 'machine_regpols': [], 'user_regpols': [] })
        pol_filelist = [fname for fname in util.traverse_dir(gpt_path) if fname.endswith('.pol')]

        for pol_file in pol_filelist:
            if self._machine_pol_path_regex.search(pol_file):
                polfiles['machine_regpols'].append(pol_file)
            else:
                polfiles['user_regpols'].append(pol_file)

        logging.debug('Polfiles: {}'.format(polfiles))

        return polfiles

