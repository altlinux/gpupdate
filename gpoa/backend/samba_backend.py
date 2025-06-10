#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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
# Facility to determine GPTs for user
try:
    from samba.gpclass import check_safe_path
except ImportError:
    from samba.gp.gpclass import check_safe_path

from .applier_backend import applier_backend
from storage import registry_factory
from gpt.gpt import gpt, get_local_gpt
from gpt.gpo_dconf_mapping import GpoInfoDconf
from util.util import (
    get_machine_name
)
from util.kerberos import (
      machine_kinit
    , machine_kdestroy
)
from util.sid import get_sid
from util.logging import log

class samba_backend(applier_backend):
    __user_policy_mode_key = '/SOFTWARE/Policies/Microsoft/Windows/System/UserPolicyMode'
    __user_policy_mode_key_win = '/Software/Policies/Microsoft/Windows/System/UserPolicyMode'

    def __init__(self, sambacreds, username, domain, is_machine):
        self.cache_path = '/var/cache/gpupdate/creds/krb5cc_{}'.format(os.getpid())
        self.__kinit_successful = machine_kinit(self.cache_path)
        if not self.__kinit_successful:
            raise Exception('kinit is not successful')
        self.storage = registry_factory()
        self.storage.set_info('domain', domain)
        machine_name = get_machine_name()
        machine_sid = get_sid(domain, machine_name, is_machine)
        self.storage.set_info('machine_name', machine_name)
        self.storage.set_info('machine_sid', machine_sid)

        # User SID to work with HKCU hive
        self.username = username
        self._is_machine_username = is_machine
        if is_machine:
            self.sid = machine_sid
        else:
            self.sid = get_sid(self.storage.get_info('domain'), self.username)

        # Samba objects - LoadParm() and CredentialsOptions()
        self.sambacreds = sambacreds

        self.cache_dir = self.sambacreds.get_cache_dir()
        self.gpo_cache_part ='gpo_cache'
        self._cached = False
        self.storage.set_info('cache_dir', os.path.join(self.cache_dir, self.gpo_cache_part))
        logdata = {'cachedir': self.cache_dir}
        log('D7', logdata)

    def __del__(self):
        if self.__kinit_successful:
            machine_kdestroy()

    def get_policy_mode(self):
        '''
        Get UserPolicyMode parameter value in order to determine if it
        is possible to work with user's part of GPT. This value is
        checked only if working for user's SID.
        '''
        upm_key = self.storage.get_key_value(self.__user_policy_mode_key)
        upm_win_key = self.storage.get_key_value(self.__user_policy_mode_key_win)
        upm = upm_key if upm_key else upm_win_key
        if upm:
            upm = int(upm)
            if upm < 0 or upm > 2:
                upm = 0
        else:
            upm = 0

        return upm

    def retrieve_and_store(self):
        '''
        Retrieve settings and strore it in a database
        '''
        # Get policies for machine at first.
        machine_gpts = []
        try:
            machine_gpts = self._get_gpts(get_machine_name(), self.storage.get_info('machine_sid'))
        except Exception as exc:
            log('F2')
            raise exc

        if self._is_machine_username:
            for gptobj in machine_gpts:
                try:
                    gptobj.merge_machine()
                except Exception as exc:
                    logdata = {}
                    logdata['msg'] = str(exc)
                    log('E26', logdata)

        # Load user GPT values in case user's name specified
        # This is a buggy implementation and should be tested more
        else:
            user_gpts = []
            try:
                user_gpts = self._get_gpts(self.username, self.sid)
            except Exception as exc:
                log('F3')
                raise exc

            # Merge user settings if UserPolicyMode set accordingly
            # and user settings (for HKCU) are exist.
            policy_mode = self.get_policy_mode()
            logdata = {'mode': upm2str(policy_mode), 'sid': self.sid}
            log('D152', logdata)

            if policy_mode < 2:
                for gptobj in user_gpts:
                    try:
                        gptobj.merge_user()
                    except Exception as exc:
                        logdata = {}
                        logdata['msg'] = str(exc)
                        log('E27', logdata)

            if policy_mode > 0:
                for gptobj in machine_gpts:
                    try:
                        gptobj.sid = self.sid
                        gptobj.merge_user()
                    except Exception as exc:
                        logdata = {}
                        logdata['msg'] = str(exc)
                        log('E63', logdata)

    def _check_sysvol_present(self, gpo):
        '''
        Check if there is SYSVOL path for GPO assigned
        '''
        self._cached = False
        if not gpo.file_sys_path:
            # GPO named "Local Policy" has no entry by its nature so
            # no reason to print warning.
            if gpo.display_name in self.storage._dict_gpo_name_version_cache.keys():
                gpo.file_sys_path = self.storage._dict_gpo_name_version_cache.get(gpo.display_name, {}).get('correct_path')
                self._cached = True
                return True
            elif 'Local Policy' != gpo.name:
                logdata = {'gponame': gpo.name}
                log('W4', logdata)
            return False
        return True

    def _get_gpts(self, username, sid):
        gpts = []

        log('D45', {'username': username, 'sid': sid})
        # util.windows.smbcreds
        gpos = self.sambacreds.update_gpos(username)
        log('D46')
        for gpo in gpos:
            if self._check_sysvol_present(gpo):
                if not self._cached:
                    path = check_safe_path(gpo.file_sys_path).upper()
                    slogdata = {'sysvol_path': gpo.file_sys_path, 'gpo_name': gpo.display_name, 'gpo_path': path}
                    log('D30', slogdata)
                    gpt_abspath = os.path.join(self.cache_dir, self.gpo_cache_part, path)
                else:
                    gpt_abspath = gpo.file_sys_path
                    log('D211', {'sysvol_path': gpo.file_sys_path, 'gpo_name': gpo.display_name})
                if self._is_machine_username:
                    obj = gpt(gpt_abspath, sid, None, GpoInfoDconf(gpo))
                else:
                    obj = gpt(gpt_abspath, sid, self.username, GpoInfoDconf(gpo))
                obj.set_name(gpo.display_name)
                gpts.append(obj)
            else:
                if 'Local Policy' == gpo.name:
                    gpts.append(get_local_gpt(sid))

        return gpts

def upm2str(upm_num):
    '''
    Translate UserPolicyMode to string.
    '''
    result = 'Not configured'

    if upm_num in [1, '1']:
        result = 'Merge'

    if upm_num in [2, '2']:
        result = 'Replace'

    return result
