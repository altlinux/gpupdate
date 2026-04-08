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


from util.logging import log
from .applier_frontend import applier_frontend, check_enabled
from .appliers.ini_file import Ini_file
from storage.gpp_state import GppStateManager, get_element_type_name, CLEANUP_SKIP_ACTIONS
from pathlib import Path
from util.windows import expand_windows_var

_REGISTRY_PATH_INI_ALLOW_EMPTY_SECTIONS = '/Software/BaseALT/Policies/GPUpdate/IniFilesAllowEmptySections'
_REGISTRY_PATH_INI_ALLOW_UNQUOTED_COMMAS = '/Software/BaseALT/Policies/GPUpdate/IniFilesAllowUnquotedCommas'
_REGISTRY_PATH_INI_ALLOW_SPECIAL_CHARS = '/Software/BaseALT/Policies/GPUpdate/IniFilesAllowSpecialChars'

def _is_empty_sections_allowed(storage):
    flag = storage.get_key_value(_REGISTRY_PATH_INI_ALLOW_EMPTY_SECTIONS)
    return flag and str(flag) == '1'

def _is_unquoted_commas_allowed(storage):
    flag = storage.get_key_value(_REGISTRY_PATH_INI_ALLOW_UNQUOTED_COMMAS)
    return flag and str(flag) == '1'

def _is_special_chars_allowed(storage):
    flag = storage.get_key_value(_REGISTRY_PATH_INI_ALLOW_SPECIAL_CHARS)
    return flag and str(flag) == '1'


class ini_applier(applier_frontend):
    __module_name = 'InifilesApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage):
        self.storage = storage
        self.inifiles_info = self.storage.get_ini()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.state_manager = GppStateManager()

    def _cleanup_removed_elements(self, removed_elements):
        '''Cleanup INI elements removed from GPO with removePolicy=True.'''
        for element in removed_elements:
            if element.get('action') in CLEANUP_SKIP_ACTIONS:
                continue

            try:
                path = expand_windows_var(element.get('path', ''))
                path = Path(path.replace('\\', '/'))

                if not path.exists() or path.is_dir():
                    continue

                section = element.get('section')
                prop = element.get('property')

                from util.gpoa_ini_parsing import GpoaConfigObj
                config = GpoaConfigObj(str(path))

                if section and prop:
                    if section in config and prop in config[section]:
                        del config[section][prop]
                        if not config[section]:
                            del config[section]
                        config.write()
            except Exception as exc:
                uid = element.get('uid', 'unknown')
                if element.get('bypass_errors'):
                    log('W47', {'uid': uid, 'exc': str(exc)})
                else:
                    raise

    def run(self):
        # Cleanup removed elements with removePolicy
        current_elements = [dict(ini) for ini in self.inifiles_info if not ini.disabled]
        removed = self.state_manager.find_removed('Inifiles', current_elements)
        self._cleanup_removed_elements(removed)

        # Apply current elements
        allow_empty = _is_empty_sections_allowed(self.storage)
        allow_unquoted = _is_unquoted_commas_allowed(self.storage)
        allow_special = _is_special_chars_allowed(self.storage)
        for inifile in self.inifiles_info:
            if inifile.disabled:
                continue
            element_type = get_element_type_name(inifile)
            if inifile.apply_once:
                if self.state_manager.should_skip(dict(inifile), element_type):
                    logdata = {'uid': getattr(inifile, 'uid', 'unknown')}
                    log('D240', logdata)
                    continue
            try:
                Ini_file(inifile, allow_empty_sections=allow_empty, allow_unquoted_commas=allow_unquoted, allow_special_chars=allow_special)
                if inifile.apply_once:
                    self.state_manager.mark_applied(dict(inifile), element_type)
            except Exception as exc:
                if getattr(inifile, 'bypass_errors', False):
                    logdata = {'uid': getattr(inifile, 'uid', 'unknown'), 'exc': str(exc)}
                    log('W47', logdata)
                else:
                    raise

    def apply(self):
        if self.__module_enabled:
            log('D171')
            self.run()
        else:
            log('D172')


class ini_applier_user(applier_frontend):
    __module_name = 'InifilesApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, username):
        self.username = username
        self.storage = storage
        self.inifiles_info = self.storage.get_ini()
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )
        self.state_manager = GppStateManager(username)

    def _cleanup_removed_elements(self, removed_elements):
        '''Cleanup INI elements removed from GPO with removePolicy=True.'''
        for element in removed_elements:
            if element.get('action') in CLEANUP_SKIP_ACTIONS:
                continue

            try:
                path = expand_windows_var(element.get('path', ''), self.username)
                path = Path(path.replace('\\', '/'))

                if not path.exists() or path.is_dir():
                    continue

                section = element.get('section')
                prop = element.get('property')

                from util.gpoa_ini_parsing import GpoaConfigObj
                config = GpoaConfigObj(str(path))

                if section and prop:
                    if section in config and prop in config[section]:
                        del config[section][prop]
                        if not config[section]:
                            del config[section]
                        config.write()
            except Exception as exc:
                uid = element.get('uid', 'unknown')
                if element.get('bypass_errors'):
                    log('W47', {'uid': uid, 'exc': str(exc)})
                else:
                    raise

    def run(self):
        # Cleanup removed elements with removePolicy
        current_elements = [dict(ini) for ini in self.inifiles_info if not ini.disabled]
        removed = self.state_manager.find_removed('Inifiles', current_elements)
        self._cleanup_removed_elements(removed)

        # Apply current elements
        allow_empty = _is_empty_sections_allowed(self.storage)
        allow_unquoted = _is_unquoted_commas_allowed(self.storage)
        allow_special = _is_special_chars_allowed(self.storage)
        for inifile in self.inifiles_info:
            if inifile.disabled:
                continue
            element_type = get_element_type_name(inifile)
            if inifile.apply_once:
                if self.state_manager.should_skip(dict(inifile), element_type):
                    logdata = {'uid': getattr(inifile, 'uid', 'unknown')}
                    log('D240', logdata)
                    continue
            try:
                Ini_file(inifile, self.username, allow_empty_sections=allow_empty, allow_unquoted_commas=allow_unquoted, allow_special_chars=allow_special)
                if inifile.apply_once:
                    self.state_manager.mark_applied(dict(inifile), element_type)
            except Exception as exc:
                if getattr(inifile, 'bypass_errors', False):
                    logdata = {'uid': getattr(inifile, 'uid', 'unknown'), 'exc': str(exc)}
                    log('W47', logdata)
                else:
                    raise

    def admin_context_apply(self):
        pass

    def user_context_apply(self):
        if self.__module_enabled:
            log('D173')
            self.run()
        else:
            log('D174')
