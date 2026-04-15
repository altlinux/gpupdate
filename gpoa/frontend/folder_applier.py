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


import re
import shutil

from util.logging import log
from util.windows import expand_windows_var

from .applier_frontend import applier_frontend, check_enabled
from .appliers.folder import Folder
from storage.gpp_state import GppStateManager, get_element_type_name, CLEANUP_SKIP_ACTIONS
from pathlib import Path


class folder_applier(applier_frontend):
    __module_name = 'FoldersApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage):
        self.storage = storage
        self.folders = self.storage.get_folders()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.state_manager = GppStateManager()

    def _cleanup_removed_elements(self, removed_elements):
        '''Cleanup folders removed from GPO with removePolicy=True.'''
        for element in removed_elements:
            if element.get('action') in CLEANUP_SKIP_ACTIONS:
                continue

            try:
                path = element.get('path')
                if not path:
                    continue

                path = expand_windows_var(path, None)
                path = Path(path.replace('\\', '/'))

                if path.exists() and path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
            except Exception as exc:
                uid = element.get('uid', 'unknown')
                if element.get('bypass_errors'):
                    log('W47', {'uid': uid, 'exc': str(exc)})
                else:
                    raise

    def apply(self):
        if self.__module_enabled:
            log('D107')
            # Cleanup removed elements with removePolicy
            current_elements = [dict(f) for f in self.folders if not f.disabled]
            removed = self.state_manager.find_removed('Folders', current_elements)
            self._cleanup_removed_elements(removed)

            # Apply current elements
            for directory_obj in self.folders:
                if directory_obj.disabled:
                    continue
                element_type = get_element_type_name(directory_obj)
                obj_dict = dict(directory_obj)
                apply_once = getattr(directory_obj, 'apply_once', False)
                bypass_errors = getattr(directory_obj, 'bypass_errors', False)
                if apply_once:
                    if self.state_manager.should_skip(obj_dict, element_type):
                        logdata = {'uid': getattr(directory_obj, 'uid', 'unknown')}
                        log('D240', logdata)
                        continue
                check = expand_windows_var(directory_obj.path).replace('\\', '/')
                win_var = re.findall(r'%.+?%', check)
                drive = re.findall(r'^[a-z A-Z]\:',check)
                if drive or win_var:
                    log('D109', {"path": directory_obj.path})
                    continue
                try:
                    fld = Folder(directory_obj)
                    fld.act()
                    if apply_once:
                        self.state_manager.mark_applied(obj_dict, element_type, element_obj=directory_obj)
                except Exception as exc:
                    if not bypass_errors:
                        raise
                    logdata = {'uid': getattr(directory_obj, 'uid', 'unknown'), 'exc': str(exc)}
                    log('W47', logdata)
        else:
            log('D108')

class folder_applier_user(applier_frontend):
    __module_name = 'FoldersApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        self.folders = self.storage.get_folders(self.username)
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )
        self.state_manager = GppStateManager(username)

    def _cleanup_removed_elements(self, removed_elements):
        '''Cleanup folders removed from GPO with removePolicy=True.'''
        for element in removed_elements:
            if element.get('action') in CLEANUP_SKIP_ACTIONS:
                continue

            try:
                path = element.get('path')
                if not path:
                    continue

                path = expand_windows_var(path, self.username)
                path = Path(path.replace('\\', '/'))

                if path.exists() and path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
            except Exception as exc:
                uid = element.get('uid', 'unknown')
                if element.get('bypass_errors'):
                    log('W47', {'uid': uid, 'exc': str(exc)})
                else:
                    raise

    def run(self):
        # Cleanup removed elements with removePolicy
        current_elements = [dict(f) for f in self.folders if not f.disabled]
        removed = self.state_manager.find_removed('Folders', current_elements)
        self._cleanup_removed_elements(removed)

        # Apply current elements
        for directory_obj in self.folders:
            if directory_obj.disabled:
                continue
            element_type = get_element_type_name(directory_obj)
            obj_dict = dict(directory_obj)
            apply_once = getattr(directory_obj, 'apply_once', False)
            bypass_errors = getattr(directory_obj, 'bypass_errors', False)
            if apply_once:
                if self.state_manager.should_skip(obj_dict, element_type):
                    logdata = {'uid': getattr(directory_obj, 'uid', 'unknown')}
                    log('D240', logdata)
                    continue
            check = expand_windows_var(directory_obj.path, self.username).replace('\\', '/')
            win_var = re.findall(r'%.+?%', check)
            drive = re.findall(r'^[a-z A-Z]\:',check)
            if drive or win_var:
                log('D110', {"path": directory_obj.path})
                continue
            try:
                fld = Folder(directory_obj, self.username)
                fld.act()
                if apply_once:
                    self.state_manager.mark_applied(obj_dict, element_type, element_obj=directory_obj)
            except Exception as exc:
                if not bypass_errors:
                    raise
                logdata = {'uid': getattr(directory_obj, 'uid', 'unknown'), 'exc': str(exc)}
                log('W47', logdata)

    def admin_context_apply(self):
        pass

    def user_context_apply(self):
        if self.__module_enabled:
            log('D111')
            self.run()
        else:
            log('D112')
