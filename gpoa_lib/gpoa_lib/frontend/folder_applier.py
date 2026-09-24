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

from ..util.logging import log
from ..util.windows_vars import expand_windows_var

from .applier_frontend import applier_frontend, DualContextApplier, check_enabled
from .appliers.folder import Folder
from ..storage.gpp_state import GppStateManager, get_element_type_name, cleanup_folder
from ..applier_result import ApplierResult, ItemStatus, STATUS_APPLIED, STATUS_PARTIAL, RESULT_SUCCESS, RESULT_FAILED, RESULT_SKIPPED


class folder_applier(applier_frontend):
    __module_name = 'FoldersApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage):
        self.storage = storage
        self.folders = self.storage.get_folders()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.state_manager = GppStateManager()

    def apply(self):
        if self.__module_enabled:
            log('I31')
            log('D107')
            items = []
            current_elements = [dict(f) for f in self.folders if not f.disabled]
            self.state_manager.cleanup_removed('Folders', current_elements, cleanup_folder)

            for directory_obj in self.folders:
                if directory_obj.disabled:
                    continue
                element_type = get_element_type_name(directory_obj)
                obj_dict = dict(directory_obj)
                apply_once = getattr(directory_obj, 'apply_once', False)
                bypass_errors = getattr(directory_obj, 'bypass_errors', False)
                uid = getattr(directory_obj, 'uid', 'unknown')
                if apply_once:
                    if self.state_manager.should_skip(obj_dict, element_type, directory_obj):
                        logdata = {'uid': uid}
                        log('D240', logdata)
                        items.append(ItemStatus(key=uid, action='skip', result=RESULT_SKIPPED))
                        continue
                check = expand_windows_var(directory_obj.path).replace('\\', '/')
                win_var = re.findall(r'%.+?%', check)
                drive = re.findall(r'^[a-z A-Z]\:',check)
                if drive or win_var:
                    log('D109', {"path": directory_obj.path})
                    items.append(ItemStatus(key=uid, action='skip', result=RESULT_SKIPPED, detail='unresolved path'))
                    continue
                try:
                    fld = Folder(directory_obj)
                    fld.act()
                    if apply_once:
                        self.state_manager.mark_applied(obj_dict, element_type, element_obj=directory_obj)
                    items.append(ItemStatus(key=uid, action='create', result=RESULT_SUCCESS))
                except Exception as exc:
                    if not bypass_errors:
                        raise
                    logdata = {'uid': uid, 'exc': str(exc)}
                    log('W47', logdata)
                    items.append(ItemStatus(key=uid, action='create', result=RESULT_FAILED, detail=str(exc)))
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='folders', status=status, items=items)
        else:
            log('D108')
            return ApplierResult.skipped('folders')

class folder_applier_user(DualContextApplier):
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

    def run(self):
        items = []
        current_elements = [dict(f) for f in self.folders if not f.disabled]
        self.state_manager.cleanup_removed('Folders', current_elements, cleanup_folder)

        for directory_obj in self.folders:
            if directory_obj.disabled:
                continue
            element_type = get_element_type_name(directory_obj)
            obj_dict = dict(directory_obj)
            apply_once = getattr(directory_obj, 'apply_once', False)
            bypass_errors = getattr(directory_obj, 'bypass_errors', False)
            uid = getattr(directory_obj, 'uid', 'unknown')
            if apply_once:
                if self.state_manager.should_skip(obj_dict, element_type, directory_obj):
                    logdata = {'uid': uid}
                    log('D240', logdata)
                    items.append(ItemStatus(key=uid, action='skip', result=RESULT_SKIPPED))
                    continue
            check = expand_windows_var(directory_obj.path, self.username).replace('\\', '/')
            win_var = re.findall(r'%.+?%', check)
            drive = re.findall(r'^[a-z A-Z]\:',check)
            if drive or win_var:
                log('D110', {"path": directory_obj.path})
                items.append(ItemStatus(key=uid, action='skip', result=RESULT_SKIPPED, detail='unresolved path'))
                continue
            try:
                fld = Folder(directory_obj, self.username)
                fld.act()
                if apply_once:
                    self.state_manager.mark_applied(obj_dict, element_type, element_obj=directory_obj)
                items.append(ItemStatus(key=uid, action='create', result=RESULT_SUCCESS))
            except Exception as exc:
                if not bypass_errors:
                    raise
                logdata = {'uid': uid, 'exc': str(exc)}
                log('W47', logdata)
                items.append(ItemStatus(key=uid, action='create', result=RESULT_FAILED, detail=str(exc)))
        return items

    def admin_context_apply(self):
        pass

    def user_context_apply(self):
        if self.__module_enabled:
            log('D111')
            items = self.run()
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='folders_user', status=status, items=items)
        else:
            log('D112')
            return ApplierResult.skipped('folders_user')
