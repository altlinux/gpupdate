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
from .appliers.envvar import Envvar
from ..storage.gpp_state import GppStateManager, get_element_type_name, cleanup_envvar
from ..applier_result import ApplierResult, ItemStatus, STATUS_APPLIED, STATUS_SKIPPED, STATUS_PARTIAL, RESULT_SUCCESS, RESULT_FAILED, RESULT_SKIPPED


class envvar_applier(applier_frontend):
    __module_name = 'EnvvarsApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage):
        self.storage = storage
        self.envvars = self.storage.get_envvars()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.state_manager = GppStateManager()

    def apply(self):
        if self.__module_enabled:
            Envvar.clear_envvar_file()
            log('I22')
            log('D134')
            items = []
            current_elements = [dict(ev) for ev in self.envvars if not ev.disabled]
            self.state_manager.cleanup_removed('Environmentvariables', current_elements, cleanup_envvar)

            envvars_filtered = [ev for ev in self.envvars if not ev.disabled]
            envvars_to_apply = []
            for ev in envvars_filtered:
                element_type = get_element_type_name(ev)
                ev_dict = dict(ev)
                apply_once = getattr(ev, 'apply_once', False)
                bypass_errors = getattr(ev, 'bypass_errors', False)
                uid = getattr(ev, 'uid', 'unknown')
                if apply_once:
                    if self.state_manager.should_skip(ev_dict, element_type, ev):
                        logdata = {'uid': uid}
                        log('D240', logdata)
                        items.append(ItemStatus(key=uid, action='skip', result=RESULT_SKIPPED))
                        continue
                envvars_to_apply.append((ev, ev_dict, apply_once, bypass_errors))
            if envvars_to_apply:
                envvar = Envvar([ev for ev, _, _, _ in envvars_to_apply], 'root')
                try:
                    envvar.act()
                    for ev, ev_dict, apply_once, _ in envvars_to_apply:
                        uid = getattr(ev, 'uid', 'unknown')
                        if apply_once:
                            ev_type = get_element_type_name(ev)
                            self.state_manager.mark_applied(ev_dict, ev_type, element_obj=ev)
                        items.append(ItemStatus(key=uid, action='set', result=RESULT_SUCCESS))
                except Exception as exc:
                    bypass_found = any(bypass for _, _, _, bypass in envvars_to_apply)
                    if bypass_found:
                        logdata = {'exc': str(exc)}
                        log('W47', logdata)
                        for ev, _, _, _ in envvars_to_apply:
                            uid = getattr(ev, 'uid', 'unknown')
                            items.append(ItemStatus(key=uid, action='set', result=RESULT_FAILED, detail=str(exc)))
                    else:
                        raise
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='envvar', status=status, items=items)
        else:
            log('D135')
            return ApplierResult.skipped('envvar')

class envvar_applier_user(DualContextApplier):
    __module_name = 'EnvvarsApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        self.envvars = self.storage.get_envvars(self.username)
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.state_manager = GppStateManager(username)

    def admin_context_apply(self):
        if self.__module_enabled:
            Envvar.clear_envvar_file(self.username)
            log('D136')
            items = []
            current_elements = [dict(ev) for ev in self.envvars if not ev.disabled]
            self.state_manager.cleanup_removed('Environmentvariables', current_elements, cleanup_envvar)

            envvars_filtered = [ev for ev in self.envvars if not ev.disabled]
            envvars_to_apply = []
            for ev in envvars_filtered:
                element_type = get_element_type_name(ev)
                ev_dict = dict(ev)
                apply_once = getattr(ev, 'apply_once', False)
                bypass_errors = getattr(ev, 'bypass_errors', False)
                uid = getattr(ev, 'uid', 'unknown')
                if apply_once:
                    if self.state_manager.should_skip(ev_dict, element_type, ev):
                        logdata = {'uid': uid}
                        log('D240', logdata)
                        items.append(ItemStatus(key=uid, action='skip', result=RESULT_SKIPPED))
                        continue
                envvars_to_apply.append((ev, ev_dict, apply_once, bypass_errors))
            if envvars_to_apply:
                envvar = Envvar([ev for ev, _, _, _ in envvars_to_apply], self.username)
                try:
                    envvar.act()
                    for ev, ev_dict, apply_once, _ in envvars_to_apply:
                        uid = getattr(ev, 'uid', 'unknown')
                        if apply_once:
                            ev_type = get_element_type_name(ev)
                            self.state_manager.mark_applied(ev_dict, ev_type, element_obj=ev)
                        items.append(ItemStatus(key=uid, action='set', result=RESULT_SUCCESS))
                except Exception as exc:
                    bypass_found = any(bypass for _, _, _, bypass in envvars_to_apply)
                    if bypass_found:
                        logdata = {'exc': str(exc)}
                        log('W47', logdata)
                        for ev, _, _, _ in envvars_to_apply:
                            uid = getattr(ev, 'uid', 'unknown')
                            items.append(ItemStatus(key=uid, action='set', result=RESULT_FAILED, detail=str(exc)))
                    else:
                        raise
            failed = sum(1 for i in items if i.result == RESULT_FAILED)
            status = STATUS_PARTIAL if failed else STATUS_APPLIED
            return ApplierResult(name='envvar_user', status=status, items=items)
        else:
            log('D137')
            return ApplierResult.skipped('envvar_user')

    def user_context_apply(self):
        pass
