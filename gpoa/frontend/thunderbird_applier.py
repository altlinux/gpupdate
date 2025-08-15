#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2024-2025 BaseALT Ltd.
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


import json
import os

from .applier_frontend import (
      applier_frontend
    , check_enabled
)
from util.logging import log
from util.util import is_machine_name
from .firefox_applier import create_dict

class thunderbird_applier(applier_frontend):
    __module_name = 'ThunderbirdApplier'
    __module_experimental = False
    __module_enabled = True
    __registry_branch = 'Software/Policies/Mozilla/Thunderbird'
    __thunderbird_policies = '/etc/thunderbird/policies'

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        self._is_machine_name = is_machine_name(self.username)
        self.policies = {}
        self.policies_json = {'policies': self.policies}
        self.thunderbird_keys = self.storage.filter_hklm_entries(self.__registry_branch)
        self.policies_gen = {}
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )


    def machine_apply(self):
        '''
        Write policies.json to Thunderbird.
        '''
        self.policies_json = create_dict(self.thunderbird_keys, self.__registry_branch)

        destfile = os.path.join(self.__thunderbird_policies, 'policies.json')
        os.makedirs(self.__thunderbird_policies, exist_ok=True)
        with open(destfile, 'w') as f:
            json.dump(self.policies_json, f)
            logdata = {'destfile': destfile}
            log('D212', logdata)

    def apply(self):
        if self.__module_enabled:
            log('D213')
            self.machine_apply()
        else:
            log('D214')
