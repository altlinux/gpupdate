from storage import sqlite_registry

from .applier_backend import applier_backend

import argparse

# Facility to determine GPTs for user
import optparse
from samba import getopt as options
from samba.gpclass import check_safe_path, check_refresh_gpo_list

# PReg object generator and parser
from samba.dcerpc import preg
from samba.dcerpc import misc
import samba.ndr

# This is needed to query AD DOMAIN name from LDAP
# using cldap_netlogon (and to replace netads utility
# invocation helper).
#from samba.dcerpc import netlogon

# This is needed by Registry.pol file search
import os
import re

# This is needed for Username and SID caching
import pickle

# Our native control facility
import util
import util.preg

# Internal error
import sys

from collections import OrderedDict

from storage import sqlite_cache

# Remove print() from code
import logging
logging.basicConfig(level=logging.DEBUG)

class samba_backend(applier_backend):
    __default_policy_path = '/usr/share/local-policy/default'
    _mahine_hive = 'HKEY_LOCAL_MACHINE'
    _user_hive = 'HKEY_CURRENT_USER'
    _machine_pol_path_pattern = '[Mm][Aa][Cc][Hh][Ii][Nn][Ee].*\.pol$'
    _user_pol_path_pattern = '[Uu][Ss][Ee][Rr].*\.pol$'

    def __init__(self, loadparm, creds, sid, dc, username):
        self.cache = sqlite_cache('regpol_cache')
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

    def retrieve_and_store(self):
        '''
        Retrieve settings and strore it in a database
        '''
        # FIXME: Please note that get_policy_set return value has no
        # meaning since we're using setting storage, so code must
        # be simplified

        # Get policies for machine at first.
        self.machine_policy_set = self.get_policy_set(util.get_machine_name(), None, True)

        self.user_policy_set = None
        # Load user GPT values in case user's name specified
        if not self._is_machine_username:
            self.user_policy_set = self.get_policy_set(self.username, self.sid, False)

    def get_policy_set(self, username, sid=None, include_local_policy=False):
        logging.info('Fetching and merging settings for user {}'.format(username))
        policy_files = self._get_pol(username)

        if include_local_policy:
            policy_files['machine_regpols'].insert(0, os.path.join(self.__default_policy_path, 'local.xml'))

        machine_entries = util.preg.merge_polfiles(policy_files['machine_regpols'])
        user_entries = util.preg.merge_polfiles(policy_files['user_regpols'], sid)

        policy_set = dict({ 'machine': machine_entries, 'user': user_entries })
        return policy_set

    def _find_regpol_files(self, gpt_path):
        '''
        Seek through SINGLE given GPT directory absolute path and return
        the dictionary of user's and machine's Registry.pol files.
        '''
        logging.debug('Finding regpols in: {}'.format(gpt_path))

        polfiles = dict({ 'machine_regpols': [], 'user_regpols': [] })
        full_traverse = util.traverse_dir(gpt_path)
        polfiles['machine_regpols'] = [fname for fname in full_traverse if self._machine_pol_path_regex.search(fname)]
        polfiles['user_regpols'] = [fname for fname in full_traverse if self._user_pol_path_regex.search(fname)]

        return polfiles

    def _check_sysvol_present(self, gpo):
        '''
        Check if there is SYSVOL path for GPO assigned
        '''
        if not gpo.file_sys_path:
            logging.warning('No SYSVOL entry assigned to GPO {}'.format(gpo.name))
            return False
        return True

    def _gpo_get_gpt_polfiles(self, gpo_obj):
        '''
        Find absolute path to SINGLE cached GPT directory and return
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
            self.cache.store(self.sid, str(policy_files))
        except:
            logging.error('Error fetching GPO list from {} for'.format(self.dc, username))
            policy_files = eval(self.cache.get_default(self.sid, OrderedDict({'machine_regpols': [], 'user_regpols': []})))
            logging.warning('Got cached PReg files {}'.format(policy_files))

        logging.info('Machine .pol file set: {}'.format(policy_files['machine_regpols']))
        logging.info('User .pol file set: {}'.format(policy_files['user_regpols']))

        return policy_files

