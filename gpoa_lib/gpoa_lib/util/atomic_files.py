# Copyright (C) 2026 BaseALT Ltd.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepare complete related files before publishing any of their contents."""

import fcntl
import os
from pathlib import Path
import shutil
import stat
import tempfile


def publish_files(contents, mode=0o644, expected=None):
    paths = {Path(path).resolve(): data for path, data in contents.items()}
    if len(paths) != len(contents):
        raise ValueError('Publication destinations must be distinct')
    if not paths:
        return
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    common = Path(os.path.commonpath([str(path.parent) for path in paths]))
    lock = os.open(common / '.gpupdate-publish.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    stages, backups, published = {}, {}, []
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for path, data in paths.items():
            old = path.stat() if path.exists() else None
            if old and not stat.S_ISREG(old.st_mode):
                raise ValueError('Publication destination is not a regular file')
            fd, temporary = tempfile.mkstemp(prefix='.gpupdate-', dir=path.parent)
            stages[path] = temporary
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                if old:
                    os.fchown(stream.fileno(), old.st_uid, old.st_gid)
                os.fchmod(stream.fileno(), stat.S_IMODE(old.st_mode) if old else mode)
                stream.flush()
                os.fsync(stream.fileno())
            if old:
                shutil.copystat(path, temporary)
                fd, backup = tempfile.mkstemp(prefix='.gpupdate-old-', dir=path.parent)
                os.close(fd)
                os.unlink(backup)
                os.link(path, backup)
                backups[path] = backup
        try:
            for filename, original in (expected or {}).items():
                if Path(filename).read_bytes() != original:
                    raise RuntimeError('Publication destination changed during preparation')
            for path, temporary in stages.items():
                os.replace(temporary, path)
                published.append(path)
        except BaseException:
            for path in reversed(published):
                if path in backups:
                    os.replace(backups[path], path)
                else:
                    path.unlink()
            raise
    finally:
        for temporary in list(stages.values()) + list(backups.values()):
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
        os.close(lock)
