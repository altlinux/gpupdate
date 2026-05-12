#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2025 BaseALT Ltd.
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

"""
Plugin message registry for GPOA plugins.

This module allows plugins to register their message codes and descriptions
without modifying the main messages.py file.
"""

import os
import sys
import inspect
import gettext
import importlib.util
from pathlib import Path

_plugin_messages = {}
_plugin_translations = {}

def _load_plugin_translations(domain):
    """
    Load translations for a specific plugin from its locale directory.

    Dynamically searches for plugin modules across the entire project.

    Args:
        domain (str): Plugin domain/prefix
    """
    try:
        # Try to find the plugin module that registered these messages
        for prefix, msgs in _plugin_messages.items():
            if prefix == domain:
                # Search through all loaded modules to find the plugin class
                for module_name, module in list(sys.modules.items()):
                    if module and hasattr(module, '__dict__'):
                        for name, obj in module.__dict__.items():
                            # Check if this is a class with the domain attribute
                            if (isinstance(obj, type) and
                                hasattr(obj, 'domain') and
                                obj.domain == domain):
                                # Found the plugin class, now find its file
                                try:
                                    plugin_file = Path(inspect.getfile(obj))
                                    plugin_dir = plugin_file.parent
                                    # Look for locale directory in plugin directory
                                    locale_dir = plugin_dir / 'locale'
                                    if locale_dir.exists():
                                        # Try to load translations
                                        lang = 'ru_RU'  # Default to Russian
                                        lc_messages_dir = locale_dir / lang / 'LC_MESSAGES'
                                        if lc_messages_dir.exists():
                                            # Look for .po files
                                            po_files = list(lc_messages_dir.glob('*.po'))
                                            for po_file in po_files:
                                                try:
                                                    translation = gettext.translation(
                                                        po_file.stem,
                                                        localedir=str(locale_dir),
                                                        languages=[lang]
                                                    )
                                                    _plugin_translations[domain] = translation
                                                    return  # Successfully loaded translations
                                                except FileNotFoundError:
                                                    continue
                                    # If not found in plugin directory, check parent directories
                                    # (for plugins that are in subdirectories)
                                    parent_dirs_to_check = [
                                        plugin_dir.parent / 'locale',  # Parent directory
                                        plugin_dir.parent.parent / 'locale'  # Grandparent directory
                                    ]
                                    for parent_locale_dir in parent_dirs_to_check:
                                        if parent_locale_dir.exists():
                                            lang = 'ru_RU'
                                            lc_messages_dir = parent_locale_dir / lang / 'LC_MESSAGES'
                                            if lc_messages_dir.exists():
                                                po_files = list(lc_messages_dir.glob('*.po'))
                                                for po_file in po_files:
                                                    try:
                                                        translation = gettext.translation(
                                                            po_file.stem,
                                                            localedir=str(parent_locale_dir),
                                                            languages=[lang]
                                                        )
                                                        _plugin_translations[domain] = translation
                                                        return  # Successfully loaded translations
                                                    except FileNotFoundError:
                                                        continue
                                except (TypeError, OSError):
                                    # Could not get file path for the class
                                    continue
                break

        # If not found through module inspection, try system-wide gpupdate plugins directory
        gpupdate_plugins_locale = Path('/usr/lib/gpupdate/plugins/locale')
        if gpupdate_plugins_locale.exists():
            lang = 'ru_RU'
            lc_messages_dir = gpupdate_plugins_locale / lang / 'LC_MESSAGES'
            if lc_messages_dir.exists():
                # Look for .po files matching the plugin prefix
                po_files = list(lc_messages_dir.glob(f'*{domain.lower()}*.po'))
                if not po_files:
                    # Try any .po file if no specific match
                    po_files = list(lc_messages_dir.glob('*.po'))

                for po_file in po_files:
                    try:
                        translation = gettext.translation(
                            po_file.stem,
                            localedir=str(gpupdate_plugins_locale),
                            languages=[lang]
                        )
                        _plugin_translations[domain] = translation
                        return  # Successfully loaded translations
                    except FileNotFoundError:
                        continue
    except Exception:
        # Silently fail if translations cannot be loaded
        pass

def register_plugin_messages(domain, messages_dict):
    """
    Register message codes for a plugin.

    Args:
        domain (str): Plugin domain/prefix
        messages_dict (dict): Dictionary mapping message codes to descriptions
    """
    _plugin_messages[domain] = messages_dict

    # Try to load plugin-specific translations
    _load_plugin_translations(domain)

def get_plugin_message(domain, code):
    """
    Get message description for a plugin-specific code.

    Args:
        domain (str): Plugin domain/prefix
        code (int): Message code

    Returns:
        str: Message description or generic message if not found
    """
    plugin_msgs = _plugin_messages.get(domain, {})
    message_text = plugin_msgs.get(code, f"Plugin {domain} message {code}")

    # Try to translate the message if translations are available
    translation = _plugin_translations.get(domain)
    if translation:
        try:
            return translation.gettext(message_text)
        except:
            pass

    return message_text

def get_all_plugin_messages():
    """
    Get all registered plugin messages.

    Returns:
        dict: Dictionary of all registered plugin messages
    """
    return _plugin_messages.copy()
