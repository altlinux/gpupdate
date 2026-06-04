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

import inspect
import gettext
import sys
from pathlib import Path

from ..util.logging import log

_plugin_messages = {}
_plugin_translations = {}

_DEFAULT_LANG = 'ru_RU'


def _try_load_translation(locale_dir, domain, lang=_DEFAULT_LANG):
    lc_messages_dir = locale_dir / lang / 'LC_MESSAGES'
    if not lc_messages_dir.exists():
        return False
    for po_file in lc_messages_dir.glob('*.po'):
        try:
            translation = gettext.translation(
                po_file.stem,
                localedir=str(locale_dir),
                languages=[lang]
            )
            _plugin_translations[domain] = translation
            return True
        except FileNotFoundError:
            continue
    return False


def _find_plugin_class_file(domain):
    for module_name, module in list(sys.modules.items()):
        if not module or not hasattr(module, '__dict__'):
            continue
        for name, obj in module.__dict__.items():
            if (isinstance(obj, type)
                    and hasattr(obj, 'domain')
                    and obj.domain == domain):
                try:
                    return Path(inspect.getfile(obj))
                except (TypeError, OSError):
                    continue
    return None


def _load_from_plugin_dir(domain, plugin_file):
    plugin_dir = plugin_file.parent
    candidate_dirs = [
        plugin_dir / 'locale',
        plugin_dir.parent / 'locale',
        plugin_dir.parent.parent / 'locale',
    ]
    for locale_dir in candidate_dirs:
        if locale_dir.exists() and _try_load_translation(locale_dir, domain):
            return True
    return False


def _load_from_system_dir(domain):
    system_locale = Path('/usr/lib/gpoa/plugins/locale')
    if not system_locale.exists():
        return False
    lc_messages_dir = system_locale / _DEFAULT_LANG / 'LC_MESSAGES'
    if not lc_messages_dir.exists():
        return False
    po_files = list(lc_messages_dir.glob(f'*{domain.lower()}*.po'))
    if not po_files:
        po_files = list(lc_messages_dir.glob('*.po'))
    for po_file in po_files:
        try:
            translation = gettext.translation(
                po_file.stem,
                localedir=str(system_locale),
                languages=[_DEFAULT_LANG]
            )
            _plugin_translations[domain] = translation
            return True
        except FileNotFoundError:
            continue
    return False


def _load_plugin_translations(domain):
    try:
        if domain not in _plugin_messages:
            return
        plugin_file = _find_plugin_class_file(domain)
        if plugin_file:
            _load_from_plugin_dir(domain, plugin_file)
        _load_from_system_dir(domain)
    except Exception as exc:
        log('D312', {'domain': domain, 'exc': str(exc)})


def register_plugin_messages(domain, messages_dict):
    _plugin_messages[domain] = messages_dict
    _load_plugin_translations(domain)


def get_plugin_message(domain, code):
    plugin_msgs = _plugin_messages.get(domain, {})
    message_text = plugin_msgs.get(code, f"Plugin {domain} message {code}")
    translation = _plugin_translations.get(domain)
    if translation:
        try:
            return translation.gettext(message_text)
        except Exception as exc:
            log('D309', {'exc': str(exc)})
    return message_text


def get_all_plugin_messages():
    return _plugin_messages.copy()
