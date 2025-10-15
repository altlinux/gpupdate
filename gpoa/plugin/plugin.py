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
from gpoa.util.util import string_to_literal_eval
from gpoa.util.logging import log
from gpoa.plugin.plugin_log import PluginLog
from gpoa.storage.dconf_registry import Dconf_registry

class plugin(ABC):
    def __init__(self, dict_dconf_db={}, username=None, fs_file_cache=None):
        self.dict_dconf_db = dict_dconf_db
        self.file_cache = fs_file_cache
        self.username = username
        self._log = None
        self.plugin_name = self.__class__.__name__
        self.enabled = self.check_enabled()

    @final
    def check_enabled(self):
        """Check if the plugin is enabled"""
        plugins_enable = Dconf_registry.get_key_value(
            '/Software/BaseALT/Policies/GPUpdate/Plugins'
        )
        plugins_list = Dconf_registry.get_key_value(
            '/Software/BaseALT/Policies/GPUpdate/PluginsList'
        )

        if not plugins_enable:
            return False

        if isinstance(plugins_list, list):
            return self.plugin_name in plugins_list
        # if the list is missing or not a list, consider the plugin enabled
        return True

    @final
    def apply(self):
        """Apply the plugin"""
        if self.enabled:
            self.run()

    @final
    def get_dict_registry(self, prefix=''):
        """Get the dictionary from the registry"""
        return  string_to_literal_eval(self.dict_dconf_db.get(prefix,{}))

    def _init_plugin_log(self, message_dict=None, locale_dir=None, domain=None):
        """Initialize plugin-specific logger with message codes."""
        self._log = PluginLog(message_dict, locale_dir, domain, self.plugin_name)

    def log_info(self, message, data=None):
        """Log info message with plugin context"""
        if self._log:
            # Try to use message code format first
            if isinstance(message, str) and len(message) > 1 and message[0].isalpha() and message[1:].isdigit():
                self._log.info(message[1:], data)
            else:
                # Fallback to simple text logging
                log("I", {"plugin": self.__class__.__name__, "message": message, "data": data})
        else:
            log("I", {"plugin": self.__class__.__name__, "message": message, "data": data})

    def log_error(self, message, data=None):
        """Log error message with plugin context"""
        if self._log:
            if isinstance(message, str) and len(message) > 1 and message[0].isalpha() and message[1:].isdigit():
                self._log.error(message[1:], data)
            else:
                log("E", {"plugin": self.__class__.__name__, "message": message, "data": data})
        else:
            log("E", {"plugin": self.__class__.__name__, "message": message, "data": data})

    def log_warning(self, message, data=None):
        """Log warning message with plugin context"""
        if self._log:
            if isinstance(message, str) and len(message) > 1 and message[0].isalpha() and message[1:].isdigit():
                self._log.warning(message[1:], data)
            else:
                log("W", {"plugin": self.__class__.__name__, "message": message, "data": data})
        else:
            log("W", {"plugin": self.__class__.__name__, "message": message, "data": data})

    def log_debug(self, message, data=None):
        """Log debug message with plugin context"""
        if self._log:
            if isinstance(message, str) and len(message) > 1 and message[0].isalpha() and message[1:].isdigit():
                self._log.debug(message[1:], data)
            else:
                log("D", {"plugin": self.__class__.__name__, "message": message, "data": data})
        else:
            log("D", {"plugin": self.__class__.__name__, "message": message, "data": data})

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
    def run(self):
        pass

