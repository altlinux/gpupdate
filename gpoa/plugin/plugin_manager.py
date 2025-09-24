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

from .plugin import plugin
from gpoa.storage import registry_factory
from gpoa.util.util import get_uid_by_username


class plugin_manager:
    def __init__(self, is_machine, username):
        self.is_machine = is_machine
        self.username = username
        self.plugins = self.load_plugins()
        log('D3')

    def run(self):
        for plugin_obj in self.plugins:
            if self.is_valid_api_object(plugin_obj):
                # Set execution context for plugins that support it
                if hasattr(plugin_obj, 'set_context'):
                    plugin_obj.set_context(self.is_machine, self.username)
                plugin_obj.run()
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
        if not spec or not spec.loader:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find plugin classes (subclasses of plugin base class)
        plugin_classes = []
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and
                issubclass(obj, plugin) and
                obj != plugin and
                not inspect.isabstract(obj)):  # Skip abstract classes
                plugin_classes.append(obj)

        # Find factory functions
        factory_funcs = []
        for name, obj in inspect.getmembers(module):
            if (inspect.isfunction(obj) and
                name.lower() in ['create_applier', 'create_plugin'] and
                callable(obj)):
                factory_funcs.append(obj)

        # Create plugin instance
        storage = registry_factory()
        if self.username and not self.is_machine:
            uid = get_uid_by_username(self.username)
            dict_dconf_db = storage.get_dictionary_from_dconf_file_db(uid)
        else:
            dict_dconf_db = storage.get_dictionary_from_dconf_file_db()

        if factory_funcs:
            # Use factory function if available
            plugin_instance = factory_funcs[0](dict_dconf_db, self.username)
        elif plugin_classes:
            # Use first found plugin class
            plugin_instance = plugin_classes[0](dict_dconf_db, self.username)
        else:
            return None

        # Initialize plugin logger if not already initialized
        if hasattr(plugin_instance, '_init_plugin_log') and not hasattr(plugin_instance, '_log'):
            # Auto-detect locale directory for this plugin
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
                plugin_instance._init_plugin_log(
                    plugin_prefix=getattr(plugin_instance, 'plugin_prefix', '000'),
                    locale_dir=str(locale_candidate)
                )

        return plugin_instance

        return None

    def is_valid_api_object(self, obj):
        return isinstance(obj, plugin)
