import logging
import subprocess
import socket
import sys
import os
import pwd

from samba.gpclass import get_dc_hostname
from samba.netcmd.common import netcmd_get_domain_infos_via_cldap
import samba.gpo
import pysss_nss_idmap

from xml.etree import ElementTree
from samba.gp_parse.gp_pol import GPPolParser

from storage import cache_factory

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
    try:
        samba_dc = get_dc_hostname(creds, lp)

        if samba_dc != dc and dc != None:
            logging.debug('Samba DC setting is {} and is overwritten by user setting {}'.format(samba_dc, dc))
            return dc
        return samba_dc
    except:
        logging.error('Unable to determine DC hostname')
    return None

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

def is_machine_name(name):
     return name == get_machine_name()

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
    logging.debug('Ticket check succeed')
    return True

def get_domain_name(lp, creds, dc):
    '''
    Get current Active Directory domain name
    '''
    try:
        # Get CLDAP record about domain
        # Look and python/samba/netcmd/domain.py for more examples
        res = netcmd_get_domain_infos_via_cldap(lp, None, dc)
        logging.info('Found domain via CLDAP: {}'.format(res.dns_domain))

        return res.dns_domain
    except:
        logging.error('Unable to retrieve domain name via CLDAP query')
    return None

def traverse_dir(root_dir):
    filelist = []
    for root, dirs, files in os.walk(root_dir):
        for filename in files:
            filelist.append(os.path.join(root, filename))
    return filelist

def get_sid(domain, username):
    '''
    Lookup SID not only using wbinfo or sssd but also using own cache
    '''
    cached_sids = cache_factory('sid_cache')
    domain_username = '{}\\{}'.format(domain, username)
    sid = 'local-{}'.format(username)
    sid = cached_sids.get_default(domain_username, sid)

    try:
        sid = wbinfo_getsid(domain, username)
    except:
        sid = 'local-{}'.format(username)
        logging.warning('Error getting SID using wbinfo, will use cached SID: {}'.format(sid))

    logging.debug('Working with SID: {}'.format(sid))

    cached_sids.store(domain_username, sid)

    return sid

def get_homedir(username):
    '''
    Query password database for user's home directory.
    '''
    return pwd.getpwnam(username).pw_dir

def mk_homedir_path(username, homedir_path):
    homedir = get_homedir(username)
    uid = pwd.getpwnam(username).pw_uid

    elements = homedir_path.split('/')
    longer_path = homedir
    for elem in elements:
        os.makedirs(longer_path, exist_ok=True)
        os.chown(homedir, uid=uid, gid=-1)
        longer_path = os.path.join(longer_path, elem)
        logging.debug('Created directory {} for user {}'.format(longer_path, username))
