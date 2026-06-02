#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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

from abc import ABC, abstractmethod
from typing import final
from ..util.util import string_to_literal_eval
from ..util.logging import log
from .plugin_log import PluginLog
from ..storage.dconf_registry import Dconf_registry

class plugin(ABC):
    '''
    Abstract base class for all plugins (both built-in and external).

    Provides ``apply()``, ``apply_user()``, ``get_dict_registry()``,
    and structured logging via ``_init_plugin_log()`` / ``log()``.

    Parameters
    ----------
    dict_dconf_db : dict
        Policy data (usually from ``StorageAdapter.get_dict()`` or
        ``plugin_manager``).
    username : str, optional
        Target username for user-scoped plugins.
    fs_file_cache : object, optional
        File cache instance.
    registry_path : str, optional
        Custom registry subkey prefix for this plugin.
    '''
    def __init__(self, dict_dconf_db={}, username=None, fs_file_cache=None, registry_path=None):
        self.dict_dconf_db = dict_dconf_db
        self.file_cache = fs_file_cache
        self.username = username
        self._log = None
        self._registry_path = registry_path
        self.plugin_name = self.__class__.__name__

    @final
    def apply(self, **kwargs):
        """Apply the plugin with current privileges"""
        self.run(**kwargs)

    @final
    def apply_user(self, username, **kwargs):
        """Apply the plugin with user privileges"""
        from .util.system import with_privileges

        def run_with_user():
            try:
                result = self.run(**kwargs)
                return {"success": True, "result": result}
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        try:
            execution_result = with_privileges(username, run_with_user)
            if execution_result and execution_result.get("success"):
                result = execution_result.get("result", True)
                return result
            else:
                return False
        except:
            return False

    @final
    def get_dict_registry(self, prefix=''):
        """Get the dictionary from the registry"""
        return  string_to_literal_eval(self.dict_dconf_db.get(prefix,{}))

    def _init_plugin_log(self, message_dict=None, locale_dir=None, domain=None):
        """Initialize plugin-specific logger with message codes."""
        self._log = PluginLog(message_dict, locale_dir, domain, self.plugin_name)

    def log(self, message_code, data=None):
        """
        Log message using plugin-specific logger with message codes.

        Args:
            message_code (str): Message code in format 'W1', 'E2', etc.
            data (dict): Additional data for message formatting
        """
        if self._log:
            self._log(message_code, data)
        else:
            # Fallback to basic logging
            level_char = message_code[0] if message_code else 'E'
            log(level_char, {"plugin": self.__class__.__name__, "message": f"Message {message_code}", "data": data})

    @abstractmethod
    def run(self, **kwargs):
        pass

