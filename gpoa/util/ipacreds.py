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
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import smbc
import os
import re
from ipalib import api
from pathlib import Path
from storage.dconf_registry import Dconf_registry, extract_display_name_version
from util.util import get_uid_by_username
from .ipa import ipaopts
from util.logging import log

class ipacreds(ipaopts):
    def __init__(self):
        super().__init__()
        self.smb_context = smbc.Context(use_kerberos=True)
        self.gpo_list = []

    def update_gpos(self, username):
        gpos = []
        try:
            if not api.isdone('bootstrap'):
                api.bootstrap(context='cli')
            if not api.isdone('finalize'):
                api.finalize()
            api.Backend.rpcclient.connect()
            try:
                server = self.get_server()
                is_machine = (username == self.get_machine_name())
                if is_machine:
                    result = api.Command.chain_resolve_for_host(username)
                else:
                    result = api.Command.chain_resolve_for_user(username)
                policies_list = result["result"]
                try:
                    if is_machine:
                        dconf_dict = Dconf_registry.get_dictionary_from_dconf_file_db(save_dconf_db=True)
                    else:
                        uid = get_uid_by_username(username)
                        dconf_dict = Dconf_registry.get_dictionary_from_dconf_file_db(uid, save_dconf_db=True)
                    dict_gpo_name_version = extract_display_name_version(dconf_dict, username)
                except Exception as exc:
                    logdata = {'exc': str(exc)}
                    log('D235', logdata)
                    dict_gpo_name_version = {}

                for policy in policies_list:
                    class SimpleGPO:
                        def __init__(self, policy_data):
                            self.display_name = policy_data.get('name', 'Unknown')
                            self.file_sys_path = policy_data.get('file_system_path', '')
                            self.version = int(policy_data.get('version', 0))
                            self.flags = int(policy_data.get('flags', 0))
                            self.link = policy_data.get('link', 'Unknown')
                            guid_match = re.search(r'\{[^}]+\}', self.file_sys_path)
                            self.name = guid_match.group(0) if guid_match else f"policy_{id(self)}"

                    gpo = SimpleGPO(policy)
                    if (gpo.display_name in dict_gpo_name_version.keys() and
                        dict_gpo_name_version.get(gpo.display_name, {}).get('version') == str(gpo.version)):

                        cached_path = dict_gpo_name_version.get(gpo.display_name, {}).get('correct_path')
                        if cached_path and Path(cached_path).exists():
                            gpo.file_sys_path = cached_path
                            ldata = {'gpo_name': gpo.display_name, 'gpo_uuid': gpo.name, 'file_sys_path_cache': True}
                        else:
                            ldata = {'gpo_name': gpo.display_name, 'gpo_uuid': gpo.name, 'file_sys_path': gpo.file_sys_path}
                    else:
                        ldata = {'gpo_name': gpo.display_name, 'gpo_uuid': gpo.name, 'file_sys_path': gpo.file_sys_path}
                    gpos.append(gpo)
            finally:
                api.Backend.rpcclient.disconnect()

        except Exception as exc:
            logdata = {'exc': str(exc)}
            log('E78', logdata)
        return gpos, server

    def get_domain(self):
        return super().get_domain()

    def get_server(self):
        return super().get_server()

    def get_cache_dir(self):
        return super().get_cache_dir()
