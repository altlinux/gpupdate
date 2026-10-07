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


from ..util.logging import log

from .applier_frontend import applier_frontend, DualContextApplier, check_enabled
from .appliers.file_cp import Execution_check, Files_cp, str2bool as check_str2bool
from ..storage.gpp_state import GppStateManager, get_element_type_name, cleanup_file
from ..applier_result import ApplierResult, ItemStatus, STATUS_APPLIED, STATUS_PARTIAL, RESULT_SUCCESS, RESULT_FAILED, RESULT_SKIPPED
from ..util.util import homedir_exists

SECURE_PERMS_KEY = 'Software/BaseALT/Policies/GroupPolicies/Files/SecurePermissionsDisabled'


def is_secure_permissions_enabled(storage):
    disabled_entries = storage.filter_hklm_entries(SECURE_PERMS_KEY)
    disabled_entry = disabled_entries.first() if disabled_entries else None
    if disabled_entry and check_str2bool(disabled_entry.data):
        log('D261', {})
        return False
    return True


class file_applier(applier_frontend):
    __module_name = 'FilesApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, file_cache):
        self.storage = storage
        self.exe_check = Execution_check(storage)
        self.file_cache = file_cache
        self.files = self.storage.get_files()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.state_manager = GppStateManager()
        self.secure_permissions = is_secure_permissions_enabled(self.storage)

    def run(self):
        items = []
        current_elements = [dict(f) for f in self.files if not f.disabled]
        self.state_manager.cleanup_removed('Files', current_elements, cleanup_file)

        for file in self.files:
            if file.disabled:
                continue
            element_type = get_element_type_name(file)
            file_dict = dict(file)
            self.state_manager.restore_file_targets(file_dict, file)
            apply_once = getattr(file, 'apply_once', False)
            bypass_errors = getattr(file, 'bypass_errors', False)
            uid = getattr(file, 'uid', 'unknown')
            if apply_once:
                if self.state_manager.should_skip(file_dict, element_type, file):
                    logdata = {'uid': uid}
                    log('D240', logdata)
                    items.append(ItemStatus(key=uid, action='skip', result=RESULT_SKIPPED))
                    continue
            try:
                Files_cp(file, self.file_cache, self.exe_check, secure_permissions=self.secure_permissions)
                if apply_once:
                    self.state_manager.mark_applied(file_dict, element_type, element_obj=file)
                items.append(ItemStatus(key=uid, action='copy', result=RESULT_SUCCESS))
            except Exception as exc:
                if not bypass_errors:
                    raise
                logdata = {'uid': uid, 'exc': str(exc)}
                log('W47', logdata)
                items.append(ItemStatus(key=uid, action='copy', result=RESULT_FAILED, detail=str(exc)))
        return items

    def apply(self):
        if self.__module_enabled:
            log('I32')
            log('D167')
            items = self.run()
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='files', status=status, items=items)
        else:
            log('D168')
            return ApplierResult.skipped('files')

class file_applier_user(DualContextApplier):
    __module_name = 'FilesApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, file_cache, username):
        self.storage = storage
        self.file_cache = file_cache
        self.username = username
        self.exe_check = Execution_check(storage)
        self.files = self.storage.get_files(self.username)
        self.__module_enabled = check_enabled(
              self.storage
            , self.__module_name
            , self.__module_experimental
        )
        self.state_manager = GppStateManager(username)
        self.secure_permissions = is_secure_permissions_enabled(self.storage)

    def run(self):
        items = []
        current_elements = [dict(f) for f in self.files if not f.disabled]
        self.state_manager.cleanup_removed('Files', current_elements, cleanup_file)

        for file in self.files:
            if file.disabled:
                continue
            element_type = get_element_type_name(file)
            file_dict = dict(file)
            self.state_manager.restore_file_targets(file_dict, file)
            apply_once = getattr(file, 'apply_once', False)
            bypass_errors = getattr(file, 'bypass_errors', False)
            uid = getattr(file, 'uid', 'unknown')
            if apply_once:
                if self.state_manager.should_skip(file_dict, element_type, file):
                    logdata = {'uid': uid}
                    log('D240', logdata)
                    items.append(ItemStatus(key=uid, action='skip', result=RESULT_SKIPPED))
                    continue
            try:
                Files_cp(file, self.file_cache, self.exe_check, self.username, secure_permissions=self.secure_permissions)
                if apply_once:
                    self.state_manager.mark_applied(file_dict, element_type, element_obj=file)
                items.append(ItemStatus(key=uid, action='copy', result=RESULT_SUCCESS))
            except Exception as exc:
                if not bypass_errors:
                    raise
                logdata = {'uid': uid, 'exc': str(exc)}
                log('W47', logdata)
                items.append(ItemStatus(key=uid, action='copy', result=RESULT_FAILED, detail=str(exc)))
        return items

    def admin_context_apply(self):
        if self.__module_enabled:
            if not homedir_exists(self.username):
                log('W7', {'username': self.username})
                return ApplierResult.skipped(
                    'files_user',
                    'User home directory does not exist; file policy deferred',
                )
            log('D169')
            items = self.run()
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='files_user', status=status, items=items)
        else:
            log('D170')
            return ApplierResult.skipped('files_user')

    def user_context_apply(self):
        pass
