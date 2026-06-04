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

from .applier_frontend import applier_frontend, check_enabled
from .appliers.envvar import Envvar
from ..storage.gpp_state import GppStateManager, get_element_type_name, cleanup_envvar


class envvar_applier(applier_frontend):
    __module_name = 'EnvvarsApplier'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage):
        self.storage = storage
        self.envvars = self.storage.get_envvars()
        Envvar.clear_envvar_file()
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.state_manager = GppStateManager()

    def apply(self):
        if self.__module_enabled:
            log('D134')
            # Cleanup removed elements with removePolicy
            current_elements = [dict(ev) for ev in self.envvars if not ev.disabled]
            self.state_manager.cleanup_removed('Environmentvariables', current_elements, cleanup_envvar)

            # Apply current elements
            envvars_filtered = [ev for ev in self.envvars if not ev.disabled]
            envvars_to_apply = []
            for ev in envvars_filtered:
                element_type = get_element_type_name(ev)
                ev_dict = dict(ev)
                apply_once = getattr(ev, 'apply_once', False)
                bypass_errors = getattr(ev, 'bypass_errors', False)
                if apply_once:
                    if self.state_manager.should_skip(ev_dict, element_type):
                        logdata = {'uid': getattr(ev, 'uid', 'unknown')}
                        log('D240', logdata)
                        continue
                envvars_to_apply.append((ev, ev_dict, apply_once, bypass_errors))
            if envvars_to_apply:
                envvar = Envvar([ev for ev, _, _, _ in envvars_to_apply], 'root')
                try:
                    envvar.act()
                    for ev, ev_dict, apply_once, _ in envvars_to_apply:
                        if apply_once:
                            ev_type = get_element_type_name(ev)
                            self.state_manager.mark_applied(ev_dict, ev_type, element_obj=ev)
                except Exception as exc:
                    bypass_found = any(bypass for _, _, _, bypass in envvars_to_apply)
                    if bypass_found:
                        logdata = {'exc': str(exc)}
                        log('W47', logdata)
                    else:
                        raise
        else:
            log('D135')

class envvar_applier_user(applier_frontend):
    __module_name = 'EnvvarsApplierUser'
    __module_experimental = False
    __module_enabled = True

    def __init__(self, storage, username):
        self.storage = storage
        self.username = username
        self.envvars = self.storage.get_envvars(self.username)
        Envvar.clear_envvar_file(username)
        self.__module_enabled = check_enabled(self.storage, self.__module_name, self.__module_experimental)
        self.state_manager = GppStateManager(username)

    def admin_context_apply(self):
        if self.__module_enabled:
            log('D136')
            # Cleanup removed elements with removePolicy
            current_elements = [dict(ev) for ev in self.envvars if not ev.disabled]
            self.state_manager.cleanup_removed('Environmentvariables', current_elements, cleanup_envvar)

            # Apply current elements
            envvars_filtered = [ev for ev in self.envvars if not ev.disabled]
            envvars_to_apply = []
            for ev in envvars_filtered:
                element_type = get_element_type_name(ev)
                ev_dict = dict(ev)
                apply_once = getattr(ev, 'apply_once', False)
                bypass_errors = getattr(ev, 'bypass_errors', False)
                if apply_once:
                    if self.state_manager.should_skip(ev_dict, element_type):
                        logdata = {'uid': getattr(ev, 'uid', 'unknown')}
                        log('D240', logdata)
                        continue
                envvars_to_apply.append((ev, ev_dict, apply_once, bypass_errors))
            if envvars_to_apply:
                envvar = Envvar([ev for ev, _, _, _ in envvars_to_apply], self.username)
                try:
                    envvar.act()
                    for ev, ev_dict, apply_once, _ in envvars_to_apply:
                        if apply_once:
                            ev_type = get_element_type_name(ev)
                            self.state_manager.mark_applied(ev_dict, ev_type, element_obj=ev)
                except Exception as exc:
                    bypass_found = any(bypass for _, _, _, bypass in envvars_to_apply)
                    if bypass_found:
                        logdata = {'exc': str(exc)}
                        log('W47', logdata)
                    else:
                        raise
        else:
            log('D137')

    def user_context_apply(self):
        pass
