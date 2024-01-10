#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2022 BaseALT Ltd.
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

from .applier_frontend import (
      applier_frontend
    , check_enabled
)

import json
import os
from util.logging import log
from util.util import is_machine_name, string_to_literal_eval

class yandex_browser_applier(applier_frontend):
    __module_name = 'YandexBrowserApplier'
    __module_enabled = True
    __module_experimental = False
    __registry_branch = 'Software\\Policies\\YandexBrowser'
    __managed_policies_path = '/etc/opt/yandex/browser/policies/managed'
    __recommended_policies_path = '/etc/opt/yandex/browser/policies/recommended'

    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username
        self._is_machine_name = is_machine_name(self.username)
        yandex_filter = '{}%'.format(self.__registry_branch)
        self.yandex_keys = self.storage.filter_hklm_entries(yandex_filter)

        self.policies_json = dict()

        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )

    def machine_apply(self):
        '''
        Apply machine settings.
        '''

        destfile = os.path.join(self.__managed_policies_path, 'policies.json')

        try:
            recommended__json = self.policies_json.pop('Recommended')
        except:
            recommended__json = {}

        #Replacing all nested dictionaries with a list
        dict_item_to_list = (
            lambda target_dict :
                {key:[*val.values()] if type(val) == dict else string_to_literal_eval(val) for key,val in target_dict.items()}
            )
        os.makedirs(self.__managed_policies_path, exist_ok=True)
        with open(destfile, 'w') as f:
            json.dump(dict_item_to_list(self.policies_json), f)
            logdata = dict()
            logdata['destfile'] = destfile
            log('D185', logdata)

        destfilerec = os.path.join(self.__recommended_policies_path, 'policies.json')
        os.makedirs(self.__recommended_policies_path, exist_ok=True)
        with open(destfilerec, 'w') as f:
            json.dump(dict_item_to_list(recommended__json), f)
            logdata = dict()
            logdata['destfilerec'] = destfilerec
            log('D185', logdata)


    def apply(self):
        '''
        All actual job done here.
        '''
        if self.__module_enabled:
            log('D183')
            self.create_dict(self.yandex_keys)
            self.machine_apply()
        else:
            log('D184')

    def get_valuename_typeint(self):
        '''
        List of keys resulting from parsing chrome.admx with parsing_chrom_admx_intvalues.py
        '''
        valuename_typeint = (['DefaultPageSaveSettings',
                            'DefaultUploadSetting',
                            'YandexAutoLaunchMode',
                            'DefaultClipboardSetting',
                            'DefaultFileSystemReadGuardSetting',
                            'DefaultFileSystemWriteGuardSetting',
                            'DefaultImagesSetting',
                            'DefaultJavaScriptJitSetting',
                            'DefaultJavaScriptSetting',
                            'DefaultLocalFontsSetting',
                            'DefaultPopupsSetting',
                            'DefaultSensorsSetting',
                            'DefaultSerialGuardSetting',
                            'DefaultWebBluetoothGuardSetting',
                            'DefaultWebHidGuardSetting',
                            'DefaultWebUsbGuardSetting',
                            'DefaultWindowManagementSetting',
                            'SafeSitesFilterBehavior',
                            'YandexUserFeedbackMode',
                            'TurboSettings',
                            'SidePanelMode',
                            'RestoreOnStartup',
                            'RestoreOnStartup_recommended',
                            'BrowserSwitcherParsingMode',
                            'DefaultNotificationsSetting',
                            'YandexPowerSavingMode',
                            'ChromeVariations',
                            'DeveloperToolsAvailability',
                            'DownloadRestrictions',
                            'NetworkPredictionOptions',
                            'DownloadRestrictions_recommended',
                            'NetworkPredictionOptions_recommended',
                            'DefaultCookiesSetting',
                            'DefaultGeolocationSetting',
                            'IncognitoModeAvailability',
                            'DefaultPrintingSettings',
                            'DefaultPluginsSetting',
                            'DefaultInsecureContentSetting',
                            'PasswordProtectionWarningTrigger',
                            'SafeBrowsingProtectionLevel',
                            'SafeBrowsingProtectionLevel_recommended'])
        return valuename_typeint


    def get_boolean(self,data):
        if data in ['0', 'false', None, 'none', 0]:
            return False
        if data in ['1', 'true', 1]:
            return True
    def get_parts(self, hivekeyname):
        '''
        Parse registry path string and leave key parameters
        '''
        parts = hivekeyname.replace(self.__registry_branch, '').split('\\')
        return parts


    def create_dict(self, yandex_keys):
        '''
        Collect dictionaries from registry keys into a general dictionary
        '''
        counts = dict()
        #getting the list of keys to read as an integer
        valuename_typeint = self.get_valuename_typeint()
        for it_data in yandex_keys:
            branch = counts
            try:
                if type(it_data.data) is bytes:
                    it_data.data = it_data.data.decode(encoding='utf-16').replace('\x00','')
                parts = self.get_parts(it_data.hive_key)
                #creating a nested dictionary from elements
                for part in parts[:-1]:
                    branch = branch.setdefault(part, {})
                #dictionary key value initialization
                if it_data.type == 4:
                    if it_data.valuename in valuename_typeint:
                        branch[parts[-1]] = int(it_data.data)
                    else:
                        branch[parts[-1]] = self.get_boolean(it_data.data)
                else:
                    if it_data.data[0] == '[' and it_data.data[-1] == ']':
                        try:
                            branch[parts[-1]] = json.loads(str(it_data.data))
                        except:
                            branch[parts[-1]] = str(it_data.data).replace('\\', '/')
                    else:
                        branch[parts[-1]] = str(it_data.data).replace('\\', '/')

            except Exception as exc:
                logdata = dict()
                logdata['Exception'] = exc
                logdata['keyname'] = it_data.keyname
                log('D178', logdata)
        try:
            self.policies_json = counts['']
        except:
            self.policies_json = {}
