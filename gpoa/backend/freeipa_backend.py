#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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
import smbc
import re
import tempfile
import shutil
import sys

from .applier_backend import applier_backend
from pathlib import Path
from gpt.gpt import gpt, get_local_gpt, get_preftype, get_parser
from gpt.gpo_dconf_mapping import GpoInfoDconf
from storage import registry_factory
from storage.dconf_registry import Dconf_registry, extract_display_name_version
from storage.fs_file_cache import fs_file_cache
from util.logging import log
from util.util import get_uid_by_username
from util.kerberos import (
      machine_kinit
    , machine_kdestroy
)


class freeipa_backend(applier_backend):
    def __init__(self, ipacreds, username, domain, is_machine):
        self.ipacreds = ipacreds
        self.cache_path = '/var/cache/gpupdate/creds/krb5cc_{}'.format(os.getpid())
        self.__kinit_successful = False
        self.__kinit_successful = machine_kinit(self.cache_path, "freeipa")
        if not self.__kinit_successful:
            raise Exception('kinit is not successful')

        self.storage = registry_factory()
        self.storage.set_info('domain', domain)

        machine_name = self.ipacreds.get_machine_name()
        self.storage.set_info('machine_name', machine_name)
        self.username = machine_name if is_machine else username
        self._is_machine_username = is_machine

        self.cache_dir = self.ipacreds.get_cache_dir()
        self.gpo_cache_part = 'gpo_cache'
        self.gpo_cache_dir = os.path.join(self.cache_dir, self.gpo_cache_part)
        self.storage.set_info('cache_dir', self.gpo_cache_dir)
        self.file_cache = fs_file_cache("freeipa_gpo", username)
        logdata = {'cachedir': self.cache_dir}
        log('D7', logdata)

    def __del__(self):
        if not sys.is_finalizing():
            try:
                self.close()
            except Exception:
                pass

    def close(self):
        if getattr(self, '_freeipa_backend__kinit_successful', False):
            self.__kinit_successful = False
            machine_kdestroy(self.cache_path)

    def retrieve_and_store(self):
        '''
        Retrieve settings and store it in a database - FreeIPA version
        '''
        try:
            if self._is_machine_username:
                dconf_dict = Dconf_registry.get_dictionary_from_dconf_file_db(save_dconf_db=True)
            else:
                uid = get_uid_by_username(self.username)
                dconf_dict = Dconf_registry.get_dictionary_from_dconf_file_db(uid, save_dconf_db=True)
        except Exception as e:
            logdata = {'msg': str(e)}
            log('E72', logdata)

        if self._is_machine_username:
            machine_gpts = []

            try:
                machine_name = self.storage.get_info('machine_name')
                machine_gpts = self._get_gpts(machine_name)
                machine_gpts.reverse()

            except Exception as exc:
                logdata = {'msg': str(exc)}
                log('E17', logdata)
                raise

            for i, gptobj in enumerate(machine_gpts):
                try:
                    gptobj.merge_machine(strict=True)
                except Exception as exc:
                    logdata = {'msg': str(exc)}
                    log('E26', logdata)
                    raise
        else:
            user_gpts = []
            try:
                user_gpts = self._get_gpts(self.username)
                user_gpts.reverse()
            except Exception as exc:
                logdata = {'msg': str(exc)}
                log('E17', logdata)
                raise
            for i, gptobj in enumerate(user_gpts):
                try:
                    gptobj.merge_user(strict=True)
                except Exception as exc:
                    logdata = {'msg': str(exc)}
                    log('E27', logdata)
                    raise

    def _get_gpts(self, username):
        gpts = []
        gpos, server = self.ipacreds.update_gpos(username)
        if not server:
            raise ValueError('FreeIPA policy server is unavailable')
        if not gpos:
            gpts.append(get_local_gpt())
            return gpts

        cached_gpos = []
        download_gpos = []

        for i, gpo in enumerate(gpos):
            if gpo.file_sys_path.startswith('/'):
                if os.path.exists(gpo.file_sys_path):
                    logdata = {'gpo_name': gpo.display_name, 'path': gpo.file_sys_path}
                    log('D11', logdata)
                    cached_gpos.append(gpo)
                else:
                    download_gpos.append(gpo)
            else:
                if self._check_sysvol_present(gpo):
                    download_gpos.append(gpo)
                else:
                    logdata = {'gpo_name': gpo.display_name}
                    log('W4', logdata)
                    raise ValueError('Policy has no usable source: {}'.format(gpo.display_name))

        if download_gpos:
            try:
                self._download_gpos(download_gpos, server)
                logdata = {'count': len(download_gpos)}
                log('D50', logdata)
            except Exception as e:
                logdata = {'msg': str(e), 'count': len(download_gpos)}
                log('E35', logdata)
                raise
        else:
            log('D211', {})

        # Cache state must not affect chain precedence.
        for gpo in gpos:
            gpt_abspath = gpo.file_sys_path
            if not os.path.exists(gpt_abspath):
                logdata = {'path': gpt_abspath, 'gpo_name': gpo.display_name}
                log('W12', logdata)
                raise FileNotFoundError(gpt_abspath)

            if self._is_machine_username:
                obj = gpt(gpt_abspath, None, GpoInfoDconf(gpo))
            else:
                obj = gpt(gpt_abspath, self.username, GpoInfoDconf(gpo))

            obj.set_name(gpo.display_name)
            gpts.append(obj)

        local_gpt = get_local_gpt()
        gpts.append(local_gpt)
        logdata = {'total_count': len(gpts), 'downloaded_count': len(download_gpos)}
        log('I2', logdata)
        return gpts

    def _check_sysvol_present(self, gpo):
        if not gpo.file_sys_path:
            if getattr(gpo, 'name', '') != 'Local Policy':
                logdata = {'gponame': getattr(gpo, 'name', 'Unknown')}
                log('W4', logdata)
            return False

        if gpo.file_sys_path.startswith('\\\\'):
            return True

        elif gpo.file_sys_path.startswith('/'):
            if os.path.exists(gpo.file_sys_path):
                return True
            else:
                return False

        else:
            return False

    def _download_gpos(self, gpos, server):
        cache_dir = self.ipacreds.get_cache_dir()
        domain = self.ipacreds.get_domain().upper()
        gpo_cache_dir = os.path.join(cache_dir, domain, 'POLICIES')
        os.makedirs(gpo_cache_dir, exist_ok=True)

        for gpo in gpos:
            if not gpo.file_sys_path:
                raise ValueError('Policy source is missing')
            smb_remote_path = None
            snapshot = None
            try:
                smb_remote_path = self._convert_to_smb_path(gpo.file_sys_path, server)
                if not gpo.name or Path(gpo.name).name != gpo.name or gpo.name in ('.', '..'):
                    raise ValueError('Invalid policy identifier')
                # Immutable snapshots let concurrent readers finish using the old
                # path. Only the completed path is published in policy metadata.
                snapshot = tempfile.mkdtemp(prefix='.snapshot-', dir=gpo_cache_dir)
                os.chmod(snapshot, 0o755)
                local_gpo_path = os.path.join(snapshot, gpo.name)
                self._download_gpo_directory(smb_remote_path, local_gpo_path)
                self._validate_snapshot(local_gpo_path)
                gpo.file_sys_path = local_gpo_path

            except Exception as e:
                logdata = {
                    'msg': str(e),
                    'gpo_name': gpo.display_name,
                    'smb_path': smb_remote_path,
                }
                log('E38', logdata)
                if snapshot:
                    shutil.rmtree(snapshot)
                raise

    @staticmethod
    def _validate_snapshot(path):
        for entry in Path(path).rglob('*'):
            if entry.is_file():
                parts = [part.casefold() for part in entry.relative_to(path).parts]
                if not parts or parts[0] not in ('machine', 'user'):
                    continue
                registry = len(parts) == 2 and parts[1] == 'registry.pol'
                preference = (len(parts) == 4 and parts[1] == 'preferences'
                              and parts[3] == parts[2] + '.xml')
                scripts = len(parts) == 3 and parts[1:] == ['scripts', 'scripts.ini']
                if scripts:
                    # Validate syntax without constructing Script objects or
                    # advancing their global execution-number counters.
                    import configparser
                    parser = configparser.ConfigParser()
                    with entry.open(encoding='utf-16') as source:
                        parser.read_file(source)
                    continue
                if not registry and not preference:
                    continue
                pref_type = get_preftype(entry)
                if pref_type is not None:
                    # Parsing must complete before the new version is accepted.
                    get_parser(pref_type)(str(entry))

    def _convert_to_smb_path(self, windows_path, server):
        match = re.search(r'\\\\[^\\]+\\(.+)', windows_path)
        if not match:
            raise Exception(f"Invalid Windows path format: {windows_path}")
        relative_path = match.group(1).replace('\\', '/').lower()
        smb_url = f"smb://{server}/{relative_path}"

        return smb_url

    def _download_gpo_directory(self, remote_smb_path, local_path):
        os.makedirs(local_path, exist_ok=True)
        try:
            directory = self.file_cache.samba_context.opendir(remote_smb_path)
            try:
                entries = directory.getdents()
            finally:
                # smbc.Dir closes its native handle on destruction, not via close().
                # Release it before descending into the next directory.
                del directory
            for entry in entries:
                if entry.name in [".", ".."]:
                    continue
                if '/' in entry.name or '\\' in entry.name:
                    raise ValueError('Invalid directory entry')
                remote_entry_path = f"{remote_smb_path}/{entry.name}"
                local_entry_path = os.path.join(local_path, entry.name)
                if entry.smbc_type == smbc.DIR:
                    self._download_gpo_directory(remote_entry_path, local_entry_path)
                elif entry.smbc_type == smbc.FILE:
                    try:
                        os.makedirs(os.path.dirname(local_entry_path), exist_ok=True)
                        self.file_cache.store(remote_entry_path, Path(local_entry_path), checked=True)
                    except Exception as e:
                        logdata = {'exception': str(e), 'file': entry.name}
                        log('W30', logdata)
                        raise
                else:
                    raise ValueError('Unsupported policy file type: {}'.format(entry.name))
        except Exception as e:
            logdata = {'exception': str(e), 'remote_folder_path': remote_smb_path}
            log('W31', logdata)
            raise
