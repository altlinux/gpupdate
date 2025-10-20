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

import importlib.util
import inspect
from pathlib import Path

from gpoa.util.logging import log
from gpoa.util.paths import gpupdate_plugins_path
from gpoa.util.util import string_to_literal_eval

from .plugin import plugin
from gpoa.storage import registry_factory
from gpoa.storage.fs_file_cache import fs_file_cache
from gpoa.util.util import get_uid_by_username


class plugin_manager:
    def __init__(self, is_machine, username):
        self.is_machine = is_machine
        self.username = username
        self.file_cache = fs_file_cache('file_cache', self.username)
        self.list_plugins = []
        self.dict_dconf_db = self.get_dict_dconf_db()
        self.filling_settings()
        self.plugins = self.load_plugins()
        log('D3')

    def get_dict_dconf_db(self):
        dconf_storage = registry_factory()
        if self.username and not self.is_machine:
            uid = get_uid_by_username(self.username)
            dict_dconf_db = dconf_storage.get_dictionary_from_dconf_file_db(uid)
        else:
            dict_dconf_db = dconf_storage.get_dictionary_from_dconf_file_db()
        return dict_dconf_db

    def filling_settings(self):
        """Filling in settings"""
        dict_gpupdate_key = string_to_literal_eval(
            self.dict_dconf_db.get('Software/BaseALT/Policies/GPUpdate',{}))
        self.plugins_enable = dict_gpupdate_key.get('Plugins')
        self.plugins_list = dict_gpupdate_key.get('PluginsList')

    def check_enabled_plugin(self, plugin_name):
        """Check if the plugin is enabled"""
        if not self.plugins_enable:
            return False

        if isinstance(self.plugins_list, list):
            return plugin_name in self.plugins_list
        # if the list is missing or not a list, consider the plugin enabled
        return True

    def run(self):
        """Run the plugins with appropriate privileges"""
        for plugin_obj in self.plugins:
            if self.is_valid_api_object(plugin_obj):
                # Set execution context for plugins that support it
                if hasattr(plugin_obj, 'set_context'):
                    plugin_obj.set_context(self.is_machine, self.username)
                if self.check_enabled_plugin(plugin_obj.plugin_name):
                    log('D4', {'plugin_name': plugin_obj.plugin_name})

                    # Use apply_user for user context, apply for machine context
                    if not self.is_machine and self.username:
                        result = plugin_obj.apply_user(self.username)
                        if result is False:
                            log('W46', {'plugin_name': plugin_obj.plugin_name, 'username': self.username})
                    else:
                        plugin_obj.apply()
                else:
                    log('D236', {'plugin_name': plugin_obj.plugin_name})
            else:
                log('W44', {'plugin_name': getattr(plugin_obj, 'plugin_name', 'unknown')})

    def load_plugins(self):
        """Load plugins from multiple directories"""
        plugins = []

        # Default plugin directories
        plugin_dirs = [
            # Frontend plugins
            Path(gpupdate_plugins_path()).absolute(),
            # System-wide plugins
            Path("/usr/lib/gpupdate/plugins")
        ]

        for plugin_dir in plugin_dirs:
            if plugin_dir.exists() and plugin_dir.is_dir():
                plugins.extend(self._load_plugins_from_directory(plugin_dir))

        return plugins

    def _load_plugins_from_directory(self, directory):
        """Load plugins from a specific directory"""
        plugins = []

        for file_path in directory.glob("*.py"):
            if file_path.name == "__init__.py":
                continue

            try:
                plugin_obj = self._load_plugin_from_file(file_path)
                if plugin_obj:
                    plugins.append(plugin_obj)
            except Exception as exc:
                log('W45', {'plugin_file': file_path.name, 'error': str(exc)})

        return plugins

    def _load_plugin_from_file(self, file_path):
        """Load a single plugin from a Python file"""
        module_name = file_path.stem

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader or module_name in self.list_plugins:
            return None
        # Save the list of names to prevent repetition
        self.list_plugins.append(module_name)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)


        # Find factory functions based on context
        factory_funcs = []
        target_factory_names = []

        if self.is_machine:
            target_factory_names = ['create_machine_applier', 'create_plugin']
        else:
            target_factory_names = ['create_user_applier', 'create_plugin']

        for name, obj in inspect.getmembers(module):
            if (inspect.isfunction(obj) and
                name.lower() in target_factory_names and
                callable(obj)):
                factory_funcs.append(obj)

        # Create plugin instance


        if factory_funcs:
            # Use factory function if available
            plugin_instance = factory_funcs[0](self.dict_dconf_db, self.username, self.file_cache)
        else:
            # No suitable factory function found for this context
            return None

        # Auto-detect locale directory for this plugin and initialize/update logger
        if hasattr(plugin_instance, '_init_plugin_log'):
            plugin_file = file_path
            plugin_dir = plugin_file.parent

            # First try: locale directory in plugin's own directory
            locale_candidate = plugin_dir / 'locale'

            # Second try: common locale directory for frontend plugins
            if not locale_candidate.exists() and 'frontend_plugins' in str(plugin_dir):
                frontend_plugins_dir = plugin_dir.parent
                common_locale_dir = frontend_plugins_dir / 'locale'
                if common_locale_dir.exists():
                    locale_candidate = common_locale_dir

            # Third try: system-wide gpupdate plugins locale directory
            if not locale_candidate.exists():
                gpupdate_plugins_locale = Path('/usr/lib/gpupdate/plugins/locale')
                if gpupdate_plugins_locale.exists():
                    locale_candidate = gpupdate_plugins_locale

            if locale_candidate.exists():
                # If logger already exists, reinitialize it with the correct locale directory
                if hasattr(plugin_instance, '_log') and plugin_instance._log is not None:
                    # Save message_dict and domain from existing logger
                    message_dict = getattr(plugin_instance._log, 'message_dict', None)
                    domain = getattr(plugin_instance._log, 'domain', None)

                    # Reinitialize logger with proper locale directory
                    plugin_instance._log = None
                else:
                    message_dict = None
                    domain = None

                # Get domain from plugin instance or use class name
                if not domain:
                    domain = getattr(plugin_instance, 'domain', plugin_instance.__class__.__name__.lower())

                # Initialize plugin logger with the found locale directory
                plugin_instance._init_plugin_log(
                    message_dict=message_dict,
                    locale_dir=str(locale_candidate),
                    domain=domain
                )

        return plugin_instance

        return None

    def is_valid_api_object(self, obj):
        """Check if the object is a valid plugin API object"""
        return isinstance(obj, plugin)
