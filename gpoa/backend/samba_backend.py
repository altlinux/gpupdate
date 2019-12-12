import logging
import os
# Facility to determine GPTs for user
from samba.gpclass import check_safe_path, check_refresh_gpo_list

from .applier_backend import applier_backend
from storage import cache_factory, registry_factory
from gpt import gpt, get_local_gpt
import util
import util.preg

class samba_backend(applier_backend):
    __default_policy_path = '/usr/share/local-policy/default'

    def __init__(self, loadparm, creds, dc, username, domain):
        # User SID to work with HKCU hive
        self.username = username
        self.domain = domain
        self._is_machine_username = util.is_machine_name(self.username)
        self.sid = util.get_sid(self.domain, self.username)
        if not self._is_machine_username:
            self.machine_sid = util.get_sid(domain, util.get_machine_name())
        else:
            self.machine_sid = self.sid

        self.storage = registry_factory('registry')
        self.cache = cache_factory('regpol_cache')
        self.gpo_names = cache_factory('gpo_names')

        # Samba objects - LoadParm() and CredentialsOptions()
        self.loadparm = loadparm
        self.creds = creds
        self.dc = dc

        self.cache_dir = self.loadparm.get('cache directory')
        logging.debug('Cache directory is: {}'.format(self.cache_dir))

    def retrieve_and_store(self):
        '''
        Retrieve settings and strore it in a database
        '''
        # Get policies for machine at first.
        machine_gpts = self._get_gpts(util.get_machine_name(), self.machine_sid)
        for gptobj in machine_gpts:
            gptobj.merge()

        # Load user GPT values in case user's name specified
        # This is a buggy implementation and should be tested more
        if not self._is_machine_username:
            user_gpts = self._get_gpts(self.username, self.sid)
            for gptobj in user_gpts:
                gptobj.merge(self.sid)

    def _check_sysvol_present(self, gpo):
        '''
        Check if there is SYSVOL path for GPO assigned
        '''
        if not gpo.file_sys_path:
            logging.warning('No SYSVOL entry assigned to GPO {}'.format(gpo.name))
            return False
        return True

    def _get_gpts(self, username, sid):
        gpts = list()

        try:
            gpos = util.get_gpo_list(self.dc, self.creds, self.loadparm, username)

            # GPT replication function
            try:
                check_refresh_gpo_list(self.dc, self.loadparm, self.creds, gpos)
            except:
                logging.error('Unable to replicate GPTs from {} for {}'.format(self.dc, username))

            for gpo in gpos:
                if self._check_sysvol_present(gpo):
                    logging.debug('Found SYSVOL entry {} for GPO {}'.format(gpo.file_sys_path, gpo.name))
                    path = check_safe_path(gpo.file_sys_path).upper()
                    gpt_abspath = os.path.join(self.cache_dir, 'gpo_cache', path)
                    print('Creating GPT object')
                    obj = gpt(gpt_abspath, sid)
                    obj.set_name(gpo.name)
                    print(obj)
                    logging.debug('Path: {}'.format(path))
                    gpts.append(obj)
                else:
                    if 'Local Policy' == gpo.name:
                        gpts.append(get_local_gpt(sid))
        except Exception as exc:
            print(exc)
            logging.error('Error fetching GPO list from {} for {}'.format(self.dc, username))

        print('GPTs found:')
        for gptobj in gpts:
            print(gptobj)
        print('---')

        return gpts
