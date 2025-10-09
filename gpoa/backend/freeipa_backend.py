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

from util.kerberos import (
      machine_kinit
    , machine_kdestroy
)
import os
from .applier_backend import applier_backend
from storage import registry_factory
from util.logging import log
import smbc
from pathlib import Path
from gpt.gpt import gpt, get_local_gpt
import stat
from gpt.gpo_dconf_mapping import GpoInfoDconf
from storage.dconf_registry import Dconf_registry, extract_display_name_version
from util.util import get_uid_by_username

class freeipa_backend(applier_backend):
    def __init__(self, ipacreds, username, domain, is_machine):
        self.ipacreds = ipacreds
        self.cache_path = '/var/cache/gpupdate/creds/krb5cc_{}'.format(os.getpid())
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
        logdata = dict({'cachedir': self.cache_dir})
        log('D7', logdata)

    def __del__(self):
        if self.__kinit_successful:
            machine_kdestroy()

    def retrieve_and_store(self):
        '''
        Retrieve settings and store it in a database - FreeIPA version
        '''
        if self._is_machine_username:
            dconf_dict = Dconf_registry.get_dictionary_from_dconf_file_db(save_dconf_db=True)
        else:
            uid = get_uid_by_username(self.username)
            dconf_dict = Dconf_registry.get_dictionary_from_dconf_file_db(uid, save_dconf_db=True)

        if self._is_machine_username:
            machine_gpts = list()
            try:
                machine_name = self.storage.get_info('machine_name')
                machine_gpts = self._get_gpts(machine_name)
                machine_gpts.reverse()
            except Exception as exc:
                logdata = {'msg': str(exc)}
                log('E17', logdata)
            for i, gptobj in enumerate(machine_gpts):
                try:
                    gptobj.merge_machine()
                except Exception as exc:
                    logdata = {'msg': str(exc)}
                    log('E26', logdata)
        else:
            user_gpts = list()
            try:
                user_gpts = self._get_gpts(self.username)
                user_gpts.reverse()
            except Exception as exc:
                logdata = {'msg': str(exc)}
                log('E17', logdata)
            for i, gptobj in enumerate(user_gpts):
                try:
                    gptobj.merge_user()
                except Exception as exc:
                    logdata = dict({'msg': str(exc)})
                    log('E27', logdata)

    def _get_gpts(self, username):
        gpts = list()
        gpos, server = self.ipacreds.update_gpos(username)
        if not gpos:
            return gpts
        if not server:
            return gpts
        for gpo in gpos:
            gpt_abspath = gpo.file_sys_path
            if not os.path.exists(gpt_abspath):
                try:
                    self._download_single_gpo(gpo, server)
                except Exception as e:
                    if self._is_machine_username:
                        logdata = {'gpo': gpo.display_name, 'error': str(e)}
                        log('E47', logdata)
                    else:
                        logdata = {'gpo': gpo.display_name, 'error': str(e)}
                        log('E50', logdata)
                    continue

            if not os.path.exists(gpt_abspath):
                log('D211', {'gpo': gpo.display_name, 'path': gpt_abspath})
                continue

            if self._is_machine_username:
                obj = gpt(gpt_abspath, None, GpoInfoDconf(gpo))
            else:
                obj = gpt(gpt_abspath, self.username, GpoInfoDconf(gpo))
            obj.set_name(gpo.display_name)
            gpts.append(obj)

        local_gpt = get_local_gpt()
        gpts.append(local_gpt)
        return gpts

    def _download_single_gpo(self, gpo, server):
        """Downloading one GPO"""
        if not gpo.file_sys_path or gpo.file_sys_path.startswith('/'):
            return
        try:
            smb_context = smbc.Context(use_kerberos=1)
            cache_dir = self.ipacreds.get_cache_dir()

            domain = self.ipacreds.get_domain().upper()
            gpo_cache_dir = os.path.join(cache_dir, domain, 'POLICIES')
            os.makedirs(gpo_cache_dir, exist_ok=True)

            smb_remote_path = self._convert_to_smb_path(gpo.file_sys_path, server)
            local_gpo_path = os.path.join(gpo_cache_dir, gpo.name)
            os.makedirs(local_gpo_path, exist_ok=True)
            logdata = {'gpo': gpo.display_name, 'server': server}
            log('D49', logdata)

            self._download_files_recursively(smb_context, smb_remote_path, local_gpo_path)
            gpo.file_sys_path = local_gpo_path

            logdata = {'gpo': gpo.display_name, 'path': local_gpo_path}
            log('D46', logdata)

        except Exception as e:
            if self._is_machine_username:
                logdata = {'gpo': gpo.display_name, 'error': str(e)}
                log('E47', logdata)
            else:
                logdata = {'gpo': gpo.display_name, 'error': str(e)}
                log('E50', logdata)
            raise

    def _convert_to_smb_path(self, windows_path, server):
        import re
        match = re.search(r'\\\\[^\\]+\\(.+)', windows_path)
        if not match:
            raise Exception(f"Invalid Windows path format: {windows_path}")
        relative_path = match.group(1).replace('\\', '/').lower()
        smb_url = f"smb://{server}/{relative_path}"

        return smb_url

    def _download_files_recursively(self, smb_context, remote_folder_path, local_folder_path):
        try:
            opendir = smb_context.opendir(remote_folder_path)
            for file_entry in opendir.getdents():
                if file_entry.name in [".", ".."]:
                    continue
                remote_file_path = f"{remote_folder_path}/{file_entry.name}"
                local_file_path = os.path.join(local_folder_path, file_entry.name)
                if file_entry.smbc_type == smbc.DIR:
                    os.makedirs(local_file_path, exist_ok=True)
                    self._download_files_recursively(smb_context, remote_file_path, local_file_path)
                elif file_entry.smbc_type == smbc.FILE:
                    try:
                        remote_file = smb_context.open(remote_file_path, os.O_RDONLY)
                        with open(local_file_path, "wb") as local_file:
                            local_file.write(remote_file.read())
                        remote_file.close()
                    except Exception as e:
                        logdata = dict({'exception': str(e), 'file': file_entry.name})
                        log('W30', logdata)
        except Exception as e:
            logdata = dict({'exception': str(e), 'remote_folder_path': remote_folder_path})
            log('W31', logdata)