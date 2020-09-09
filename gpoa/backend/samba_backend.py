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

import os
# Facility to determine GPTs for user
from samba.gpclass import check_safe_path, check_refresh_gpo_list

from .applier_backend import applier_backend
from storage import cache_factory, registry_factory
from gpt.gpt import gpt, get_local_gpt
from util.util import (
    get_machine_name,
    is_machine_name
)
from util.kerberos import (
      machine_kinit
    , machine_kdestroy
)
from util.windows import get_sid
import util.preg
from util.logging import log

class samba_backend(applier_backend):

    def __init__(self, sambacreds, username, domain, is_machine):
        self.cache_path = '/var/cache/gpupdate/creds/krb5cc_{}'.format(os.getpid())
        self.__kinit_successful = machine_kinit(self.cache_path)
        self.storage = registry_factory('registry')
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

        self.cache = cache_factory('regpol_cache')
        self.gpo_names = cache_factory('gpo_names')

        # Samba objects - LoadParm() and CredentialsOptions()
        self.sambacreds = sambacreds

        self.cache_dir = self.sambacreds.get_cache_dir()
        logdata = dict({'cachedir': self.cache_dir})
        log('D7', logdata)

    def __del__(self):
        if self.__kinit_successful:
            machine_kdestroy()

    def retrieve_and_store(self):
        '''
        Retrieve settings and strore it in a database
        '''
        # Get policies for machine at first.
        machine_gpts = list()
        try:
            machine_gpts = self._get_gpts(get_machine_name(), self.storage.get_info('machine_sid'))
        except Exception as exc:
            log('F2')
            raise exc
        self.storage.wipe_hklm()
        self.storage.wipe_user(self.storage.get_info('machine_sid'))
        for gptobj in machine_gpts:
            try:
                gptobj.merge()
            except Exception as exc:
                logdata = dict()
                logdata['msg'] = str(exc)
                log('E26', logdata)

        # Load user GPT values in case user's name specified
        # This is a buggy implementation and should be tested more
        if not self._is_machine_username:
            user_gpts = list()
            try:
                user_gpts = self._get_gpts(self.username, self.sid)
            except Exception as exc:
                log('F3')
                raise exc
            self.storage.wipe_user(self.sid)
            for gptobj in user_gpts:
                try:
                    gptobj.merge()
                except Exception as exc:
                    logdata = dict()
                    logdata['msg'] = str(exc)
                    log('E27', logdata)

    def _check_sysvol_present(self, gpo):
        '''
        Check if there is SYSVOL path for GPO assigned
        '''
        if not gpo.file_sys_path:
            # GPO named "Local Policy" has no entry by its nature so
            # no reason to print warning.
            if 'Local Policy' != gpo.name:
                logdata = dict({'gponame': gpo.name})
                log('W4', logdata)
            return False
        return True

    def _get_gpts(self, username, sid):
        gpts = list()

        log('D45')
        # util.windows.smbcreds
        gpos = self.sambacreds.update_gpos(username)
        log('D46')
        for gpo in gpos:
            if self._check_sysvol_present(gpo):
                path = check_safe_path(gpo.file_sys_path).upper()
                slogdata = dict({'sysvol_path': gpo.file_sys_path, 'gpo_name': gpo.display_name, 'gpo_path': path})
                log('D30', slogdata)
                gpt_abspath = os.path.join(self.cache_dir, 'gpo_cache', path)
                obj = gpt(gpt_abspath, sid)
                obj.set_name(gpo.display_name)
                gpts.append(obj)
            else:
                if 'Local Policy' == gpo.name:
                    gpts.append(get_local_gpt(sid))

        return gpts

