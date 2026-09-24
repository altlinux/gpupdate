"""Checked access to regular files in user-controlled directories."""
import os
import stat
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_regular_file(path, mode='r+'):
    path = Path(path)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        flags = os.O_NOFOLLOW | os.O_NONBLOCK
        flags |= os.O_RDONLY if mode == 'r' else os.O_RDWR | os.O_CREAT
        fd = os.open(path.name, flags, 0o644, dir_fd=parent)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('Expected an unshared regular file: {}'.format(path))
        stream = os.fdopen(fd, 'r' if mode == 'r' else 'r+')
        fd = None
        with stream:
            if mode == 'w':
                stream.truncate(0)
            yield stream
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)
