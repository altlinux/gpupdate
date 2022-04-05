#! /usr/bin/env python3
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

from enum import Enum
import logging
import subprocess

from .logging import slogm

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


def get_sid(domain, username):
    '''
    Lookup SID not only using wbinfo or sssd but also using own cache
    '''
    domain_username = '{}\\{}'.format(domain, username)
    sid = 'local-{}'.format(username)

    try:
        sid = wbinfo_getsid(domain, username)
    except:
        sid = 'local-{}'.format(username)
        logging.warning(
            slogm('Error getting SID using wbinfo, will use cached SID: {}'.format(sid)))

    logging.debug(slogm('Working with SID: {}'.format(sid)))

    return sid


class IssuingAuthority(Enum):
    SECURITY_NULL_SID_AUTHORITY = 0
    SECURITY_WORLD_SID_AUTHORITY = 1
    SECURITY_LOCAL_SID_AUTHORITY = 2
    SECURITY_CREATOR_SID_AUTHORITY = 3
    SECURITY_NON_UNIQUE_AUTHORITY = 4
    SECURITY_NT_AUTHORITY = 5
    SECURITY_RESOURCE_MANAGER_AUTHORITY = 9

class SidRevision(Enum):
    FIRST = 1

# This thing exists only after "S-1-5-21-"
# Last part of full SID
# https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/81d92bba-d22b-4a8c-908a-554ab29148ab
class WellKnown21RID(Enum):
    ENTERPRISE_READONLY_DOMAIN_CONTROLLERS = 498
    ADMINISTRATOR = 500 # For machine
    GUEST = 501 # For machine
    KRBTGT = 502
    DOMAIN_ADMINS = 512
    DOMAIN_USERS = 513
    DOMAIN_GUESTS = 514
    DOMAIN_COMPUTERS = 515
    DOMAIN_CONTROLLERS = 516
    CERT_PUBLISHERS = 517
    SCHEMA_ADMINISTRATORS = 518 # For root domain
    ENTERPRISE_ADMINS = 519 # For root domain
    GROUP_POLICY_CREATOR_OWNERS = 520
    READONLY_DOMAIN_CONTROLLERS = 521
    CLONEABLE_CONTROLLERS = 522
    PROTECTED_USERS = 525
    KEY_ADMINS = 526
    ENTERPRISE_KEY_ADMINS = 527
    RAS_SERVERS = 553
    ALLOWED_RODC_PASSWORD_REPLICATION_GROUP = 571
    DENIED_RODC_PASSWORD_REPLICATION_GROUP = 572

# This thing exists only after "S-1-5-32-"
# Last part of full SID
# https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/81d92bba-d22b-4a8c-908a-554ab29148ab
class WellKnown32RID(Enum):
    BUILTIN_ADMINISTRATORS = 544
    BUILTIN_USERS = 545
    BUILTIN_GUESTS = 546
    POWER_USERS = 547
    ACCOUNT_OPERATORS = 548
    SERVER_OPERATORS = 549
    PRINTER_OPERATORS = 550
    BACKUP_OPERATORS = 551
    REPLICATOR = 552
    ALIAS_PREW2KCOMPACC = 554
    REMOTE_DESKTOP = 555
    NETWORK_CONFIGURATION_OPS = 556
    INCOMING_FOREST_TRUST_BUILDERS = 557
    PERFMON_USERS = 558
    PERFLOG_USERS = 559
    WINDOWS_AUTHORIZATION_ACCESS_GROUP = 560
    TERMINAL_SERVER_LICENSE_SERVERS = 561
    DISTRIBUTED_COM_USERS = 562
    IIS_IUSRS = 568
    CRYPTOGRAPHIC_OPERATORS = 569
    EVENT_LOG_READERS = 573
    CERTIFICATE_SERVICE_DCOM_ACCESS = 574
    RDS_REMOTE_ACCESS_SERVERS = 575
    RDS_ENDPOINT_SERVERS = 576
    RDS_MANAGEMENT_SERVERS = 577
    HYPER_V_ADMINS = 578
    ACCESS_CONTROL_ASSISTANCE_OPS = 579
    REMOTE_MANAGEMENT_USERS = 580

# This thing exists only after "S-1-5-"
class FirstSubAuthority(Enum):
    SECURITY_DIALUP_RID = 1
    SECURITY_NETWORK_RID = 2
    SECURITY_BATCH_RID = 3
    SECURITY_INTERACTIVE_RID = 4
    SECURITY_LOGON_IDS_RID = 5
    SECURITY_SERVICE_RID = 6
    SECURITY_ANONYMOUS_LOGON_RID = 7
    SECURITY_PROXY_RID = 8
    SECURITY_ENTERPRISE_CONTROLLERS_RID = 9
    SECURITY_PRINCIPAL_SELF_RID = 10
    SECURITY_AUTHENTICATED_USER_RID = 11
    SECURITY_RESTRICTED_CODE_RID = 12
    SECURITY_TERMINAL_SERVER_RID = 13
    SECURITY_LOCAL_SYSTEM_RID = 18
    SECURITY_NT_NON_UNIQUE = 21
    SECURITY_BUILTIN_DOMAIN_RID = 32
    SECURITY_WRITE_RESTRICTED_CODE_RID = 33

class SecondSubAuthority(Enum):
    DOMAIN_ALIAS_RID_ADMINS = 544

def validate_issuing_authority(ia_num):
    ia_value = None

    ia_value = int(IssuingAuthority(ia_num))

    return ia_value

def validate_sid_revision(revnum):
    rev_value = None

    rev_value = int(SidRevision(revnum))

    return rev_value

def is_sid(sid):
    # Check that SID is SID (S)
    if not sid[0] == 'S':
        return False

    # Check revision version (1 for Windows-generated SID) (R)
    if not validate_sid_revision(int(sid[2])):
        return False

    # Check issuing authority (IA)
    issuing_authority = validate_issuing_authority(int(sid[4]))
    if not issuing_authority:
        return False

    if issuing_authority == 21:
        pass
    elif issuing_authority == 32:
        pass
    else:
        pass

def sid2descr(sid):
    sids = dict()
    sids['S-1-0']    = 'Null Authority'
    sids['S-1-0-0']  = 'Nobody'
    sids['S-1-1']    = 'World Authority'
    sids['S-1-1-0']  = 'Everyone'
    sids['S-1-2']    = 'Local Authority'
    sids['S-1-2-0']  = 'Local'
    sids['S-1-3']    = 'Creator Authority'
    sids['S-1-3-0']  = 'Creator Owner'
    sids['S-1-3-1']  = 'Creator Group'
    sids['S-1-3-2']  = 'Creator Owner Server' # Since Windows 2003
    sids['S-1-3-3']  = 'Creator Group Server' # Since Windows 2003
    sids['S-1-3-4']  = 'Owner Rights'
    sids['S-1-4']    = 'Non-unique Authority'
    sids['S-1-5']    = 'NT Authority'
    sids['S-1-5-1']  = 'Dialup'
    sids['S-1-5-2']  = 'Network'
    sids['S-1-5-3']  = 'Batch'
    sids['S-1-5-4']  = 'Interactive'
    sids['S-1-5-6']  = 'Service'
    sids['S-1-5-7']  = 'Anonymous'
    sids['S-1-5-8']  = 'Proxy' # Since Windows 2003
    sids['S-1-5-9']  = 'Enterprise Domain Controllers'
    sids['S-1-5-10'] = 'Principal Self'
    sids['S-1-5-11'] = 'Authenticated Users'
    sids['S-1-5-12'] = 'Restricted Code'
    sids['S-1-5-13'] = 'Terminal Server Users'
    sids['S-1-5-14'] = 'Remote Interactive Logon'
    sids['S-1-5-15'] = 'This Organization' # Since Windows 2003
    sids['S-1-5-17'] = 'This Organization'
    sids['S-1-5-18'] = 'Local System'
    sids['S-1-5-19'] = 'NT Authority' # Local Service
    sids['S-1-5-20'] = 'NT Authority' # Network Service
    sids['S-1-5-32-544'] = 'Administrators'
    sids['S-1-5-32-545'] = 'Users'
    sids['S-1-5-32-546'] = 'Guests'
    sids['S-1-5-32-547'] = 'Power Users'
    sids['S-1-5-32-548'] = 'Account Operators'
    sids['S-1-5-32-549'] = 'Server Operators'
    sids['S-1-5-32-550'] = 'Print Operators'
    sids['S-1-5-32-551'] = 'Backup Operators'
    sids['S-1-5-32-552'] = 'Replicators'
    sids['S-1-5-32-554'] = 'Builtin\\Pre-Windows 2000 Compatible Access' # Since Windows 2003
    sids['S-1-5-32-555'] = 'Builtin\\Remote Desktop Users' # Since Windows 2003
    sids['S-1-5-32-556'] = 'Builtin\\Network Configuration Operators' # Since Windows 2003
    sids['S-1-5-32-557'] = 'Builtin\\Incoming Forest Trust Builders' # Since Windows 2003
    sids['S-1-5-32-558'] = 'Builtin\\Performance Monitor Users' # Since Windows 2003
    sids['S-1-5-32-582'] = 'Storage Replica Administrators'
    sids['S-1-5-64-10']  = 'NTLM Authentication'
    sids['S-1-5-64-14']  = 'SChannel Authentication'
    sids['S-1-5-64-21']  = 'Digest Authentication'
    sids['S-1-5-80']     = 'NT Service'

    return sids.get(sid, None)

