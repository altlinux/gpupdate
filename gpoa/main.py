#! /usr/bin/env python3

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
from backend import samba_backend
import frontend

# Internal error
import sys

# Remove print() from code
import logging
logging.basicConfig(level=logging.DEBUG)

def parse_arguments():
    arguments = argparse.ArgumentParser(description='Generate configuration out of parsed policies')
    arguments.add_argument('user',
        type=str,
        nargs='?',
        default=util.get_machine_name(),
        help='Domain username ({}) to parse policies for'.format(util.get_machine_name()))
    arguments.add_argument('--dc',
        type=str,
        help='FQDN of the domain to replicate SYSVOL from')
    arguments.add_argument('--nodomain',
        action='store_true',
        help='Operate without domain (apply local policy)')
    return arguments.parse_args()

class gpoa_controller:
    __kinit_successful = False
    __parser = optparse.OptionParser('GPO Applier')
    __args = None
    __sambaopts = options.SambaOptions(__parser)
    __credopts = options.CredentialsOptions(__parser)
    # Initialize loadparm context
    __lp = __sambaopts.get_loadparm()
    __creds = __credopts.get_credentials(__lp, fallback_machine=True)

    def __init__(self):
        self.__kinit_successful = util.machine_kinit()
        self.__args = parse_arguments()
        sid_cache = os.path.join(self.__lp.get('cache directory'), 'sid_cache.pkl')
        cached_sids = util.get_cache(sid_cache, dict())

        # Determine the default Samba DC for replication and try
        # to overwrite it with user setting.
        dc = None
        try:
            dc = util.select_dc(self.__lp, self.__creds, self.__args.dc)
        except:
            pass

        username = self.__args.user
        domain = None
        try:
            domain = util.get_domain_name(self.__lp, self.__creds, dc)
        except:
            pass
        sid = 'local-{}'.format(self.__args.user)

        domain_username = '{}\\{}'.format(domain, username)
        if domain_username in cached_sids:
            sid = cached_sids[domain_username]
            logging.info('Got cached SID {} for user {}'.format(sid, domain_username))

        try:
            sid = util.wbinfo_getsid(domain, username)
        except:
            sid = 'local-{}'.format(self.__args.user)
            logging.warning('Error getting SID using wbinfo, will use cached SID: {}'.format(sid))

        logging.info('Working with SID: {}'.format(sid))

        cached_sids[domain_username] = sid
        with open(sid_cache, 'wb') as f:
            pickle.dump(cached_sids, f, pickle.HIGHEST_PROTOCOL)
            logging.info('Cached SID {} for user {}'.format(sid, domain_username))

        back = samba_backend(self.__lp, self.__creds, sid, dc, username)

        appl = frontend.applier(sid, back)
        appl.apply_parameters()

def main():
    logging.info('Working with Samba DC')
    controller = gpoa_controller()

if __name__ == "__main__":
    main()

