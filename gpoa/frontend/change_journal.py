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

import hashlib
from pathlib import Path
import stat


_watched_paths = {}
_current_snapshots = {}
_current_snapshot_keys = {}
_changed_paths = set()
_presence_changed_paths = set()


def _normalize(path):
    if not path:
        return None
    try:
        return str(Path(path).resolve(strict=False))
    except Exception:
        return str(path)


def _kind_from_mode(st_mode):
    if stat.S_ISREG(st_mode):
        return 'file'
    if stat.S_ISDIR(st_mode):
        return 'dir'
    if stat.S_ISLNK(st_mode):
        return 'symlink'
    return 'other'


def _sha256(path_obj):
    digest = hashlib.sha256()
    with path_obj.open('rb') as file_obj:
        while True:
            chunk = file_obj.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _present_snapshot_key(stat_result):
    return (
        'present',
        stat_result.st_mode,
        stat_result.st_uid,
        stat_result.st_gid,
        stat_result.st_size,
        stat_result.st_mtime_ns,
        stat_result.st_ctime_ns,
        stat_result.st_ino,
    )


def _missing_snapshot(snapshot_key):
    return {
        'exists': False,
        'kind': None,
        'stat': None,
        'sha256': None,
        '_snapshot_key': snapshot_key,
    }


def _present_snapshot(path_obj, stat_result, snapshot_key):
    sha256 = None
    if stat.S_ISREG(stat_result.st_mode):
        try:
            sha256 = _sha256(path_obj)
        except Exception:
            sha256 = '__error__'

    return {
        'exists': True,
        'kind': _kind_from_mode(stat_result.st_mode),
        'stat': (
            stat_result.st_mode,
            stat_result.st_uid,
            stat_result.st_gid,
            stat_result.st_size,
            stat_result.st_mtime_ns,
            stat_result.st_ctime_ns,
            stat_result.st_ino,
        ),
        'sha256': sha256,
        '_snapshot_key': snapshot_key,
    }


def _snapshot(path):
    path_obj = Path(path)
    try:
        stat_result = path_obj.lstat()
        snapshot_key = _present_snapshot_key(stat_result)
    except FileNotFoundError:
        return _missing_snapshot(('absent',))
    except Exception:
        return _missing_snapshot(('error',))

    return _present_snapshot(path_obj, stat_result, snapshot_key)


def reset():
    _watched_paths.clear()
    _current_snapshots.clear()
    _current_snapshot_keys.clear()
    _changed_paths.clear()
    _presence_changed_paths.clear()


def watch(path):
    normalized = _normalize(path)
    if not normalized:
        return
    if normalized not in _watched_paths:
        _watched_paths[normalized] = _snapshot(normalized)
    _current_snapshots.pop(normalized, None)
    _current_snapshot_keys.pop(normalized, None)


def watch_many(paths):
    if not paths:
        return
    for path in paths:
        watch(path)


def record_changed(path):
    normalized = _normalize(path)
    if normalized:
        _changed_paths.add(normalized)


def record_presence_changed(path):
    normalized = _normalize(path)
    if normalized:
        _presence_changed_paths.add(normalized)
        _changed_paths.add(normalized)


def _snapshot_current(path):
    path_obj = Path(path)
    try:
        stat_result = path_obj.lstat()
        key = _present_snapshot_key(stat_result)
        snapshot_factory = lambda: _present_snapshot(path_obj, stat_result, key)
    except FileNotFoundError:
        key = ('absent',)
        snapshot_factory = lambda: _missing_snapshot(key)
    except Exception:
        key = ('error',)
        snapshot_factory = lambda: _missing_snapshot(key)

    if _current_snapshot_keys.get(path) == key:
        return _current_snapshots[path]
    current = snapshot_factory()
    _current_snapshot_keys[path] = key
    _current_snapshots[path] = current
    return current


def _presence_changed(path):
    baseline = _watched_paths.get(path)
    if baseline is None:
        return False
    current = _snapshot_current(path)
    return baseline['exists'] != current['exists']


def _changed(path):
    baseline = _watched_paths.get(path)
    if baseline is None:
        return False
    current = _snapshot_current(path)

    if baseline['exists'] != current['exists']:
        return True

    if not baseline['exists'] and not current['exists']:
        return False

    return (
        baseline['kind'] != current['kind']
        or baseline['stat'] != current['stat']
        or baseline['sha256'] != current['sha256']
    )


def query(path, mode='changed'):
    normalized = _normalize(path)
    if not normalized:
        return False
    if mode == 'presence_changed':
        if normalized in _presence_changed_paths:
            return True
        return _presence_changed(normalized)
    if normalized in _changed_paths:
        return True
    return _changed(normalized)
