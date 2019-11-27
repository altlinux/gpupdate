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
#import appliers
import util
from backend import samba_backend, local_policy_backend
import frontend

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

def parse_arguments():
    arguments = argparse.ArgumentParser(description='Generate configuration out of parsed policies')
    arguments.add_argument('user',
        type=str,
        nargs='?',
        default=get_machine_name(),
        help='Domain username ({}) to parse policies for'.format(get_machine_name()))
    arguments.add_argument('--dc',
        type=str,
        help='FQDN of the domain to replicate SYSVOL from')
    arguments.add_argument('--nodomain',
        action='store_true',
        help='Operate without domain (apply local policy)')
    return arguments.parse_args()

def apply_samba_dc(arg_dc, arg_user):
    sambaopts = options.SambaOptions(parser)
    credopts = options.CredentialsOptions(parser)
    # Initialize loadparm context
    lp = sambaopts.get_loadparm()
    creds = credopts.get_credentials(lp, fallback_machine=True)

    sid_cache = os.path.join(lp.get('cache directory'), 'sid_cache.pkl')
    cached_sids = util.get_cache(sid_cache, dict())

    util.machine_kinit()
    util.check_krb_ticket()

    # Determine the default Samba DC for replication and try
    # to overwrite it with user setting.
    dc = util.select_dc(lp, creds, arg_dc)

    username = arg_user
    domain = util.get_domain_name(lp, creds, dc)
    sid = ''

    domain_username = '{}\\{}'.format(domain, username)
    if domain_username in cached_sids:
        sid = cached_sids[domain_username]
        logging.info('Got cached SID {} for user {}'.format(sid, domain_username))

    try:
        sid = util.wbinfo_getsid(domain, username)
    except:
        logging.warning('Error getting SID using wbinfo, will use cached SID: {}'.format(sid))

    logging.info('Working with SID: {}'.format(sid))

    cached_sids[domain_username] = sid
    with open(sid_cache, 'wb') as f:
        pickle.dump(cached_sids, f, pickle.HIGHEST_PROTOCOL)
        logging.info('Cached SID {} for user {}'.format(sid, domain_username))

    back = samba_backend(lp, creds, sid, dc, username)

    appl = frontend.applier(sid, back)
    appl.apply_parameters()

def apply_local_policy(user):
    back = local_policy_backend(user)
    appl = frontend.applier('local-{}'.format(user), back)
    appl.apply_parameters()

def main():
    parser = optparse.OptionParser('GPO Applier')
    args = parse_arguments()

    if args.nodomain:
        logging.info('Working without domain - applying Local Policy')
        apply_local_policy(args.user)
    else:
        logging.info('Working with Samba DC')
        apply_samba_domain(args.dc, args.user)

if __name__ == "__main__":
    main()

