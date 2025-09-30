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

import os
import gettext
import locale
import logging
import inspect
from pathlib import Path

from gpoa.util.logging import slogm
from gpoa.plugin.messages import register_plugin_messages


class PluginLog:
    """
    Plugin logging class with message codes and translations support.

    Usage:
        log = PluginLog({
            'w': {1: 'Warning message template {param}'},
            'e': {1: 'Error message template {param}'},
            'i': {1: 'Info message template {param}'},
            'd': {1: 'Debug message template {param}'}
        }, domain='dm_applier')

        log('W1', {'param': 'value'})
    """

    def __init__(self, message_dict=None, locale_dir=None, domain=None):
        """
        Initialize plugin logger.

        Args:
            message_dict (dict): Dictionary with message templates
            locale_dir (str): Path to locale directory for translations
            domain (str): Translation domain name (required for translations)
        """
        self.message_dict = message_dict or {}
        self.locale_dir = locale_dir
        self.domain = domain or 'plugin'
        self._translation = None

        # Register plugin messages
        if message_dict:
            # Convert to flat dictionary for registration
            flat_messages = {}
            for level, level_dict in message_dict.items():
                for code, message in level_dict.items():
                    flat_messages[code] = message

            register_plugin_messages(self.domain, flat_messages)

        # Auto-detect locale directory only if explicitly None (not provided)
        # If locale_dir is an empty string or other falsy value, don't auto-detect
        if self.locale_dir is None:
            self._auto_detect_locale_dir()

        # Load translations
        self._load_translations()

    def _auto_detect_locale_dir(self):
        """Auto-detect locale directory based on plugin file location."""
        try:
            # Try to find the calling plugin module
            frame = inspect.currentframe()
            while frame:
                module = frame.f_globals.get('__name__', '')
                if module and 'plugin' in module:
                    module_file = frame.f_globals.get('__file__', '')
                    if module_file:
                        plugin_dir = Path(module_file).parent
                        # First try: locale directory in plugin's own directory
                        locale_candidate = plugin_dir / 'locale'
                        if locale_candidate.exists():
                            self.locale_dir = str(locale_candidate)
                            return
                        # Second try: common locale directory for frontend plugins
                        if 'frontend_plugins' in str(plugin_dir):
                            frontend_plugins_dir = plugin_dir.parent
                            common_locale_dir = frontend_plugins_dir / 'locale'
                            if common_locale_dir.exists():
                                self.locale_dir = str(common_locale_dir)
                                return
                frame = frame.f_back
            # Third try: relative to current working directory
            cwd_locale = Path.cwd() / 'gpoa' / 'frontend_plugins' / 'locale'
            if cwd_locale.exists():
                self.locale_dir = str(cwd_locale)
                return
            # Fourth try: relative to script location
            script_dir = Path(__file__).parent.parent.parent / 'frontend_plugins' / 'locale'
            if script_dir.exists():
                self.locale_dir = str(script_dir)
                return
            # Fifth try: system installation path for frontend plugins
            system_paths = [
                '/usr/lib/python3/site-packages/gpoa/frontend_plugins/locale',
                '/usr/local/lib/python3/site-packages/gpoa/frontend_plugins/locale'
            ]
            for path in system_paths:
                if os.path.exists(path):
                    self.locale_dir = path
                    return

            # Sixth try: system-wide gpupdate package locale directory
            gpupdate_package_locale = Path('/usr/lib/python3/site-packages/gpoa/locale')
            if gpupdate_package_locale.exists():
                self.locale_dir = str(gpupdate_package_locale)
                return

            # Seventh try: system-wide locale directory (fallback)
            system_locale_dir = Path('/usr/share/locale')
            if system_locale_dir.exists():
                self.locale_dir = str(system_locale_dir)
                return
        except:
            pass

    def _load_translations(self):
        """Load translations for the plugin using system locale."""
        if self.locale_dir:
            # Use only self.domain as the translation file name
            # This aligns with the convention that plugin translation files
            # are always named according to the domain
            domain = self.domain

            try:
                # Get system locale
                system_locale = locale.getdefaultlocale()[0]
                languages = [system_locale] if system_locale else ['ru_RU']

                # First try: load from the detected locale_dir without fallback
                try:
                    self._translation = gettext.translation(
                        domain,
                        localedir=self.locale_dir,
                        languages=languages,
                        fallback=False
                    )
                except FileNotFoundError:
                    # File not found, try with fallback
                    self._translation = gettext.translation(
                        domain,
                        localedir=self.locale_dir,
                        languages=languages,
                        fallback=True
                    )

                    # Check if we got real translations or NullTranslations
                    if isinstance(self._translation, gettext.NullTranslations):
                        # Try loading from system locale directory as fallback
                        try:
                            self._translation = gettext.translation(
                                domain,
                                localedir='/usr/share/locale',
                                languages=languages,
                                fallback=False
                            )
                        except FileNotFoundError:
                            # File not found in system directory, use fallback
                            self._translation = gettext.translation(
                                domain,
                                localedir='/usr/share/locale',
                                languages=languages,
                                fallback=True
                            )

            except Exception:
                # If any exception occurs, fall back to NullTranslations
                self._translation = gettext.NullTranslations()

            # Ensure _translation is set even if all attempts failed
            if not hasattr(self, '_translation'):
                self._translation = gettext.NullTranslations()
        else:
            self._translation = gettext.NullTranslations()

    def _get_message_template(self, level, code):
        """Get message template for given level and code."""
        level_dict = self.message_dict.get(level, {})
        return level_dict.get(code, 'Unknown message {code}')

    def _format_message(self, level, code, data=None):
        """Format message with data and apply translation."""
        template = self._get_message_template(level, code)
        # Apply translation
        translated_template = self._translation.gettext(template)
        # Format with data if provided
        if data and isinstance(data, dict):
            try:
                return translated_template.format(**data)
            except:
                return "{} | {}".format(translated_template, data)
        return translated_template

    def _get_full_code(self, level_char, code):
        """Get full message code without plugin prefix."""
        return f"{level_char}{code:05d}"

    def __call__(self, message_code, data=None):
        """
        Log a message with the given code and data.

        Args:
            message_code (str): Message code in format 'W1', 'E2', etc.
            data (dict): Additional data for message formatting
        """
        if not message_code or len(message_code) < 2:
            logging.error(slogm("Invalid message code format", {"code": message_code}))
            return
        level_char = message_code[0].lower()
        try:
            code_num = int(message_code[1:])
        except ValueError:
            logging.error(slogm("Invalid message code number", {"code": message_code}))
            return

        # Get the formatted message
        message = self._format_message(level_char, code_num, data)
        # Create full message code for logging
        full_code = self._get_full_code(level_char.upper(), code_num)
        # Format the log message like main code: [Code]| Message | data
        full_code = self._get_full_code(level_char.upper(), code_num)
        log_message = f"{self.domain}[{full_code}]| {message}"
        if data:
            log_message += f"|{data}"

        # Log with appropriate level - no kwargs needed
        if level_char == 'i':
            logging.info(slogm(log_message))
        elif level_char == 'w':
            logging.warning(slogm(log_message))
        elif level_char == 'e':
            logging.error(slogm(log_message))
        elif level_char == 'd':
            logging.debug(slogm(log_message))
        elif level_char == 'f':
            logging.fatal(slogm(log_message))
        else:
            logging.info(slogm(log_message))

    def info(self, code, data=None):
        """Log info message."""
        self(f"I{code}", data)

    def warning(self, code, data=None):
        """Log warning message."""
        self(f"W{code}", data)

    def error(self, code, data=None):
        """Log error message."""
        self(f"E{code}", data)

    def debug(self, code, data=None):
        """Log debug message."""
        self(f"D{code}", data)

    def fatal(self, code, data=None):
        """Log fatal message."""
        self(f"F{code}", data)
