#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

import fnmatch
import os

SECURE_PERMISSIONS = {
    '/etc/sudoers': 0o440,
    '/etc/crontab': 0o600,
    '/etc/crypttab': 0o600,
    '/etc/ipsec.secrets': 0o600,
    '/etc/sssd/sssd.conf': 0o600,
    '/etc/krb5.keytab': 0o600,
    '/var/kerberos/krb5kdc/kdc.conf': 0o600,
    '/var/kerberos/krb5kdc/kadm5.acl': 0o600,
    '/var/kerberos/krb5kdc/kadm5.keytab': 0o600,
    '/etc/ssh/ssh_host_rsa_key': 0o600,
    '/etc/ssh/ssh_host_ed25519_key': 0o600,
    '/etc/ssh/ssh_host_ecdsa_key': 0o600,
    '/etc/ssh/ssh_host_dsa_key': 0o600,
    '/etc/ssl/private': 0o710,
    '/etc/pki/tls/private': 0o710,
    '/etc/pki/CA/private': 0o710,
    '/etc/security/opasswd': 0o600,
    '/etc/pam_ldap.conf': 0o600,
    '/etc/nss_ldap.conf': 0o600,
    '/var/lib/samba/private/secrets.tdb': 0o600,
    '/etc/openldap/slapd.conf': 0o600,
    '/etc/openvpn/auth.txt': 0o600,
    '/etc/openvpn/*.key': 0o600,
    '/etc/wireguard/wg0.conf': 0o600,
    '~/.ssh/id_rsa': 0o600,
    '~/.ssh/id_ed25519': 0o600,
    '~/.ssh/id_ecdsa': 0o600,
    '~/.ssh/id_dsa': 0o600,
    '~/.ssh/config': 0o600,
    '~/.ssh/known_hosts': 0o600,
    '~/.netrc': 0o600,
    '~/.pgpass': 0o600,
    '~/.my.cnf': 0o600,
    '~/.aws/credentials': 0o600,
    '~/.aws/config': 0o600,
    '~/.gnupg/private-keys-v1.d/*.key': 0o600,
    '~/.google_authenticator': 0o400,
    '~/.git-credentials': 0o600,
    '~/.kube/config': 0o600,
    '~/.vault-token': 0o600,
    '~/.docker/config.json': 0o600,
    '~/.config/containers/auth.json': 0o600,
    '~/.config/gcloud/credentials.db': 0o600,
    '~/.config/gcloud/application_default_credentials.json': 0o600,
    '~/.azure/accessTokens.json': 0o600,
    '~/.azure/msal_token_cache.json': 0o600,
    '~/.oci/config': 0o600,
    '~/.terraform.d/credentials.tfrc.json': 0o600,
    '/etc/kubernetes/pki/*.key': 0o600,
    '/etc/ansible/vault_pass': 0o600,
    '/etc/containerd/config.toml': 0o600,
    '/etc/docker/daemon.json': 0o600,
    '/etc/postfix/sasl_passwd': 0o600,
    '/etc/postfix/sasl_passwd.db': 0o600,
    '/etc/dovecot/private/*.pem': 0o600,
    '/etc/exim4/passwd.client': 0o640,
    '/etc/chrony.keys': 0o640,
    '/etc/ntp/keys': 0o600,
    '/etc/sudoers.d/*': 0o440,
    '/var/spool/cron/crontabs/*': 0o600,
    '/etc/cron.d/*': 0o600,
    '/etc/mysql/mysql.conf.d/mysqld.cnf': 0o600,
    '/etc/raddb/clients.conf': 0o640,
    '/etc/raddb/users': 0o640,
    '/etc/raddb/radiusd.conf': 0o640,
    '/etc/vault.d/vault.hcl': 0o640,
    '/etc/letsencrypt/live/*/privkey.pem': 0o600,
    '/etc/letsencrypt/archive/*/privkey.pem': 0o600,
    '/etc/nginx/ssl/*.key': 0o600,
    '/etc/apache2/ssl/*.key': 0o600,
    '/etc/ssl/private/*.key': 0o600,
    '/etc/pki/tls/private/*.key': 0o600,
    '/etc/pki/CA/private/*.key': 0o600,
    '/opt/vault/tls/*.key': 0o600,
    '/etc/ssh/ssh_host_*_key': 0o600,
    '/var/lib/samba/private/krb5.conf': 0o600,
    '/var/lib/samba/private/*.keytab': 0o600,
    '/etc/grafana/grafana.ini': 0o640,
    '/etc/zabbix/zabbix_agentd.conf': 0o600,
    '/etc/zabbix/zabbix_server.conf': 0o600,
    '/etc/telegraf/telegraf.conf': 0o600,
    '/etc/gshadow': 0o600,
}

GLOB_PATTERNS = {k: v for k, v in SECURE_PERMISSIONS.items() if '*' in k}
EXACT_PATHS = {k: v for k, v in SECURE_PERMISSIONS.items() if '*' not in k}


def get_secure_permission(filepath, username=None):
    '''Check if a file path requires secure permissions.

    Args:
        filepath: Path to check (may contain ~ or be absolute)
        username: Optional username for expanding ~ paths

    Returns:
        Permission mode (int) if path matches, None otherwise
    '''
    if not filepath:
        return None

    expanded = _expand_user_path(filepath, username)

    for path, mode in EXACT_PATHS.items():
        expanded_key = _expand_user_path(path, username)
        if expanded == expanded_key:
            return mode

    for pattern, mode in GLOB_PATTERNS.items():
        expanded_pattern = _expand_user_path(pattern, username)
        if fnmatch.fnmatch(expanded, expanded_pattern):
            return mode

    return None


def get_secure_dir_permission(dirpath, username=None):
    '''Check if a directory path requires secure permissions.

    Args:
        dirpath: Absolute path to check
        username: Optional username for expanding ~ paths

    Returns:
        Permission mode (int) if path matches, None otherwise
    '''
    if not dirpath:
        return None

    expanded = _expand_user_path(dirpath, username)

    for path, mode in EXACT_PATHS.items():
        expanded_key = _expand_user_path(path, username)
        if expanded == expanded_key:
            return mode

    for pattern, mode in GLOB_PATTERNS.items():
        expanded_pattern = _expand_user_path(pattern, username)
        if fnmatch.fnmatch(expanded, expanded_pattern):
            return mode

    parent = expanded
    while parent != '/':
        for path, mode in EXACT_PATHS.items():
            expanded_key = _expand_user_path(path, username)
            if parent == expanded_key:
                return mode
        parent = os.path.dirname(parent)

    return None


def _expand_user_path(path, username=None):
    '''Expand ~ in path using the given username or root.

    Args:
        path: Path that may contain ~
        username: Optional username for expansion

    Returns:
        Expanded absolute path
    '''
    if '~' not in path:
        return path

    if username:
        import pwd
        try:
            pwent = pwd.getpwnam(username)
            home = pwent.pw_dir
        except KeyError:
            home = f'/home/{username}'
    else:
        home = '/root'

    return path.replace('~', home, 1)