import logging
import subprocess
import socket
import sys
import os
import pickle

from samba.gpclass import get_dc_hostname
from samba.netcmd.common import netcmd_get_domain_infos_via_cldap
import samba.gpo
import pysss_nss_idmap

from xml.etree import ElementTree
from samba.gp_parse.gp_pol import GPPolParser

logging.basicConfig(level=logging.DEBUG)

def get_gpo_list(dc_hostname, creds, lp, user):
    gpos = []
    ads = samba.gpo.ADS_STRUCT(dc_hostname, lp, creds)
    if ads.connect():
        #gpos = ads.get_gpo_list(creds.get_username())
        gpos = ads.get_gpo_list(user)
    logging.info('Got GPO list:')
    for gpo in gpos:
        # These setters are taken from libgpo/pygpo.c
        # print(gpo.ds_path) # LDAP entry
        logging.info('{} ({})'.format(gpo.display_name, gpo.name))
    logging.info('------')
    return gpos

def select_dc(lp, creds, dc):
    samba_dc = get_dc_hostname(creds, lp)

    if samba_dc != dc and dc != None:
        logging.debug('Samba DC setting is {} and is overwritten by user setting {}'.format(samba_dc, dc))
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
    return check_krb_ticket()

def check_krb_ticket():
    '''
    Check if Kerberos 5 ticket present
    '''
    try:
        subprocess.check_call([ 'klist', '-s' ])
        output = subprocess.check_output('klist', stderr=subprocess.STDOUT).decode()
        logging.info(output)
    except:
        logging.error('Kerberos ticket check unsuccessful')
        return False
    logging.info('Ticket check succeed')
    return True

def get_domain_name(lp, creds, dc):
    '''
    Get current Active Directory domain name
    '''
    # Get CLDAP record about domain
    # Look and python/samba/netcmd/domain.py for more examples
    res = netcmd_get_domain_infos_via_cldap(lp, None, dc)
    logging.info('Found domain via CLDAP: {}'.format(res.dns_domain))

    return res.dns_domain

def get_cache(cache_file, default_cache_obj):
    if not os.path.exists(cache_file):
        logging.info('Initializing missing cache file: {}'.format(cache_file))
        with open(cache_file, 'wb') as f:
            pickle.dump(default_cache_obj, f, pickle.HIGHEST_PROTOCOL)

    data = None
    with open(cache_file, 'rb') as f:
        data = pickle.load(f)
    logging.info('Read cache {}'.format(cache_file))

    return data

def dump_cache(cache_file, cache_obj):
    with open(cache_file, 'wb') as f:
        pickle.dump(cache_obj, f, pickle.HIGHEST_PROTOCOL)
    logging.info('Wrote cache {}'.format(cache_file))

def traverse_dir(root_dir):
    filelist = []
    for root, dirs, files in os.walk(root_dir):
        for filename in files:
            filelist.append(os.path.join(root, filename))
    return filelist

