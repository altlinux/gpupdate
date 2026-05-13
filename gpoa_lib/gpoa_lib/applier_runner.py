#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

from .storage.storage_adapter import StorageAdapter
from .storage.fs_file_cache import fs_file_cache
from .util.logging import log


_APPLIER_MAP = None


def _get_applier_map():
    global _APPLIER_MAP
    if _APPLIER_MAP is not None:
        return _APPLIER_MAP

    from .frontend.chromium_applier import chromium_applier
    from .frontend.control_applier import control_applier
    from .frontend.firefox_applier import firefox_applier
    from .frontend.firewall_applier import firewall_applier
    from .frontend.gsettings_applier import gsettings_applier
    from .frontend.kde_applier import kde_applier
    from .frontend.ntp_applier import ntp_applier
    from .frontend.package_applier import package_applier
    from .frontend.polkit_applier import polkit_applier
    from .frontend.systemd_applier import systemd_applier
    from .frontend.thunderbird_applier import thunderbird_applier
    from .frontend.yandex_browser_applier import yandex_browser_applier

    _APPLIER_MAP = {
        'control': {
            'class': control_applier,
            'branch': 'Software/BaseALT/Policies/Control',
        },
        'chromium': {
            'class': chromium_applier,
            'branch': 'Software/Policies/Google/Chrome',
            'extra': ('username',),
        },
        'firefox': {
            'class': firefox_applier,
            'branch': 'Software/Policies/Mozilla/Firefox',
            'extra': ('username',),
        },
        'thunderbird': {
            'class': thunderbird_applier,
            'branch': 'Software/Policies/Mozilla/Thunderbird',
            'extra': ('username',),
        },
        'yandex_browser': {
            'class': yandex_browser_applier,
            'branch': 'Software/Policies/YandexBrowser',
            'extra': ('username',),
        },
        'firewall': {
            'class': firewall_applier,
            'branch': r'SOFTWARE\Policies\Microsoft\WindowsFirewall\FirewallRules',
        },
        'gsettings': {
            'class': gsettings_applier,
            'branch': r'Software\BaseALT\Policies\gsettings',
            'extra': ('file_cache',),
        },
        'kde': {
            'class': kde_applier,
            'branch': 'Software/BaseALT/Policies/KDE',
        },
        'ntp': {
            'class': ntp_applier,
            'branch': r'Software\Policies\Microsoft\W32time\Parameters',
        },
        'package': {
            'class': package_applier,
            'branch': r'Software\BaseALT\Policies\Packages',
        },
        'polkit': {
            'class': polkit_applier,
            'branch': r'Software\BaseALT\Policies\Polkit',
        },
        'systemd': {
            'class': systemd_applier,
            'branch': 'Software/BaseALT/Policies/SystemdUnits',
        },
    }
    return _APPLIER_MAP


def _normalize_path(path):
    return path.replace('\\', '/')


def _join_prefix(prefix, applier_name):
    norm = prefix.replace('\\', '/').rstrip('/')
    return norm + '/' + applier_name


class ApplierRunner:
    '''
    High-level API for running appliers externally via gpoa_lib.

    Convention: last part of key path = applier name.
    Example: prefix='Software/MyOrg/Policies' + applier 'control'
             -> 'Software/MyOrg/Policies/Control'

    Usage:
        runner = ApplierRunner(db_name='mydb')
        runner.run('control')
        runner.run('control', prefix='Software/MyOrg/Policies')
        runner.run('control', keys=['Software/X/key1', 'Software/X/key2'])
    '''

    def __init__(self, db_name=None, uid=None, data=None):
        self.db_name = db_name
        self.uid = uid
        self._data = data
        self._file_cache = None

    def _get_storage(self, prefix=None, keys=None):
        if prefix:
            return StorageAdapter(db_name=self.db_name, uid=self.uid,
                                  data=self._data, prefix=prefix)
        elif keys:
            return StorageAdapter(db_name=self.db_name, uid=self.uid,
                                  data=self._data, keys=keys)
        else:
            return StorageAdapter(db_name=self.db_name, uid=self.uid,
                                  data=self._data)

    def _get_file_cache(self):
        if self._file_cache is None:
            username = self._uid_to_username(self.uid)
            self._file_cache = fs_file_cache('file_cache', username)
        return self._file_cache

    @staticmethod
    def _uid_to_username(uid):
        if uid is None:
            return None
        try:
            import pwd
            return pwd.getpwuid(uid).pw_name
        except (KeyError, ImportError):
            return None

    def create(self, applier_name, prefix=None, keys=None):
        '''
        Create an applier instance.

        Args:
            applier_name: Name from APPLIER_MAP (see list_appliers())
            prefix: Override base prefix. Applier name is appended automatically.
                    Example: prefix='Software/MyOrg/Policies' -> 'Software/MyOrg/Policies/Control'
            keys: List of specific registry keys to use

        Returns:
            Applier instance or None if applier_name not found
        '''
        amap = _get_applier_map()
        if applier_name not in amap:
            logdata = {'applier_name': applier_name, 'available': list(amap.keys())}
            log('W44', logdata)
            return None

        entry = amap[applier_name]
        applier_cls = entry['class']
        default_branch = entry.get('branch', '')

        if keys:
            storage = self._get_storage(keys=keys)
        elif prefix:
            effective_prefix = _join_prefix(prefix, applier_name)
            storage = self._get_storage(prefix=effective_prefix)
        else:
            storage = self._get_storage()

        extra = entry.get('extra', ())

        if 'file_cache' in extra:
            return applier_cls(storage, self._get_file_cache())
        elif 'username' in extra:
            return applier_cls(storage, self._uid_to_username(self.uid))

        return applier_cls(storage)

    def run(self, applier_name, prefix=None, keys=None):
        '''Create and run an applier.'''
        applier = self.create(applier_name, prefix, keys)
        if applier is not None:
            try:
                applier.apply()
            except Exception as exc:
                logdata = {'applier_name': applier_name, 'msg': str(exc)}
                log('E24', logdata)

    @staticmethod
    def list_appliers():
        '''Return list of available applier names.'''
        return list(_get_applier_map().keys())
