#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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

import os
import sys
import unittest

gpoa_dir = os.path.join(os.path.dirname(__file__), '..', '..')
gpoa_dir = os.path.abspath(gpoa_dir)
if gpoa_dir not in sys.path:
    sys.path.insert(0, gpoa_dir)

from util.secure_paths import get_secure_permission, get_secure_dir_permission


class SecurePathsExactMatchTestCase(unittest.TestCase):

    def test_etc_shadow(self):
        self.assertIsNone(get_secure_permission('/etc/shadow'))

    def test_etc_gshadow(self):
        self.assertEqual(get_secure_permission('/etc/gshadow'), 0o600)

    def test_etc_sudoers(self):
        self.assertEqual(get_secure_permission('/etc/sudoers'), 0o440)

    def test_etc_crontab(self):
        self.assertEqual(get_secure_permission('/etc/crontab'), 0o600)

    def test_etc_crypttab(self):
        self.assertEqual(get_secure_permission('/etc/crypttab'), 0o600)

    def test_etc_ssh_host_key(self):
        self.assertEqual(get_secure_permission('/etc/ssh/ssh_host_rsa_key'), 0o600)
        self.assertEqual(get_secure_permission('/etc/ssh/ssh_host_ed25519_key'), 0o600)
        self.assertEqual(get_secure_permission('/etc/ssh/ssh_host_ecdsa_key'), 0o600)
        self.assertEqual(get_secure_permission('/etc/ssh/ssh_host_dsa_key'), 0o600)

    def test_etc_sssd_conf(self):
        self.assertEqual(get_secure_permission('/etc/sssd/sssd.conf'), 0o600)

    def test_etc_krb5_keytab(self):
        self.assertEqual(get_secure_permission('/etc/krb5.keytab'), 0o600)

    def test_wireguard_conf(self):
        self.assertEqual(get_secure_permission('/etc/wireguard/wg0.conf'), 0o600)

    def test_ipsec_secrets(self):
        self.assertEqual(get_secure_permission('/etc/ipsec.secrets'), 0o600)

    def test_opasswd(self):
        self.assertEqual(get_secure_permission('/etc/security/opasswd'), 0o600)

    def test_removed_paths_not_secure(self):
        self.assertIsNone(get_secure_permission('/etc/shadow'))
        self.assertIsNone(get_secure_permission('/var/lib/mysql'))
        self.assertIsNone(get_secure_permission('/tmp/krb5cc_1000'))
        self.assertIsNone(get_secure_permission('/home/user/.bash_history'))
        self.assertIsNone(get_secure_permission('/home/user/.zsh_history'))
        self.assertIsNone(get_secure_permission('/boot/grub/grub.cfg'))

    def test_non_secure_path(self):
        self.assertIsNone(get_secure_permission('/etc/hosts'))
        self.assertIsNone(get_secure_permission('/tmp/test.txt'))
        self.assertIsNone(get_secure_permission('/usr/bin/ls'))


class SecurePathsGlobMatchTestCase(unittest.TestCase):

    def test_ssh_host_key_glob(self):
        self.assertEqual(get_secure_permission('/etc/ssh/ssh_host_rsa_key'), 0o600)
        self.assertEqual(get_secure_permission('/etc/ssh/ssh_host_ecdsa_key'), 0o600)

    def test_ssl_private_key_glob(self):
        self.assertEqual(get_secure_permission('/etc/ssl/private/server.key'), 0o600)
        self.assertEqual(get_secure_permission('/etc/ssl/private/wildcard.key'), 0o600)

    def test_nginx_ssl_key_glob(self):
        self.assertEqual(get_secure_permission('/etc/nginx/ssl/server.key'), 0o600)

    def test_apache2_ssl_key_glob(self):
        self.assertEqual(get_secure_permission('/etc/apache2/ssl/server.key'), 0o600)

    def test_letsencrypt_privkey_glob(self):
        self.assertEqual(get_secure_permission('/etc/letsencrypt/live/example.com/privkey.pem'), 0o600)
        self.assertEqual(get_secure_permission('/etc/letsencrypt/archive/example.com/privkey.pem'), 0o600)

    def test_sudoers_d_glob(self):
        self.assertEqual(get_secure_permission('/etc/sudoers.d/custom'), 0o440)
        self.assertEqual(get_secure_permission('/etc/sudoers.d/admins'), 0o440)

    def test_cron_d_glob(self):
        self.assertEqual(get_secure_permission('/etc/cron.d/daily'), 0o600)

    def test_kubernetes_key_glob(self):
        self.assertEqual(get_secure_permission('/etc/kubernetes/pki/ca.key'), 0o600)
        self.assertEqual(get_secure_permission('/etc/kubernetes/pki/apiserver.key'), 0o600)

    def test_gnupg_key_glob(self):
        result = get_secure_permission('~/.gnupg/private-keys-v1.d/ABC.key', username='testuser')
        self.assertEqual(result, 0o600)

    def test_var_spool_cron_glob(self):
        self.assertEqual(get_secure_permission('/var/spool/cron/crontabs/root'), 0o600)

    def test_pki_tls_private_key_glob(self):
        self.assertEqual(get_secure_permission('/etc/pki/tls/private/server.key'), 0o600)

    def test_pki_ca_private_key_glob(self):
        self.assertEqual(get_secure_permission('/etc/pki/CA/private/ca.key'), 0o600)


class SecurePathsUserContextTestCase(unittest.TestCase):

    def test_ssh_key_root(self):
        result = get_secure_permission('~/.ssh/id_rsa', username=None)
        self.assertEqual(result, 0o600)

    def test_ssh_key_user(self):
        result = get_secure_permission('~/.ssh/id_rsa', username='testuser')
        self.assertEqual(result, 0o600)

    def test_ssh_config_tilde_root(self):
        result = get_secure_permission('~/.ssh/config', username=None)
        self.assertEqual(result, 0o600)

    def test_ssh_config_tilde_user(self):
        result = get_secure_permission('~/.ssh/config', username='testuser')
        self.assertEqual(result, 0o600)

    def test_aws_credentials_tilde(self):
        result = get_secure_permission('~/.aws/credentials', username='testuser')
        self.assertEqual(result, 0o600)

    def test_kube_config_tilde(self):
        result = get_secure_permission('~/.kube/config', username='testuser')
        self.assertEqual(result, 0o600)

    def test_docker_config_tilde(self):
        result = get_secure_permission('~/.docker/config.json', username='testuser')
        self.assertEqual(result, 0o600)


class SecurePathsDirPermissionsTestCase(unittest.TestCase):

    def test_ssl_private_dir(self):
        self.assertEqual(get_secure_dir_permission('/etc/ssl/private'), 0o710)

    def test_pki_tls_private_dir(self):
        self.assertEqual(get_secure_dir_permission('/etc/pki/tls/private'), 0o710)

    def test_pki_ca_private_dir(self):
        self.assertEqual(get_secure_dir_permission('/etc/pki/CA/private'), 0o710)

    def test_regular_dir_no_match(self):
        self.assertIsNone(get_secure_dir_permission('/tmp'))
        self.assertIsNone(get_secure_dir_permission('/var/log'))

    def test_dir_inside_secure_dir(self):
        self.assertEqual(get_secure_dir_permission('/etc/ssl/private/subdir'), 0o710)

    def test_dir_empty_path(self):
        self.assertIsNone(get_secure_dir_permission(''))
        self.assertIsNone(get_secure_dir_permission(None))


class SecurePathsEdgeCasesTestCase(unittest.TestCase):

    def test_empty_path(self):
        self.assertIsNone(get_secure_permission(''))

    def test_none_path(self):
        self.assertIsNone(get_secure_permission(None))

    def test_similar_but_not_matching(self):
        self.assertIsNone(get_secure_permission('/etc/shadow.bak'))
        self.assertIsNone(get_secure_permission('/etc/ssh/ssh_host_rsa_key.pub'))
        self.assertIsNone(get_secure_permission('/etc/sudoers.d'))
        self.assertIsNone(get_secure_permission('/etc/hosts'))


if __name__ == '__main__':
    unittest.main()