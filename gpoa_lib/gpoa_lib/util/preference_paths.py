"""Pure effective-target calculations shared by application and cleanup."""
from pathlib import Path
from .windows_vars import expand_windows_var
from .util import get_homedir


def hidden_target(path, hidden, keep_dot=False):
    path = Path(path)
    if hidden and not (keep_dot and path.name.startswith('.')):
        return path.with_name('.' + path.name)
    return path


def folder_target(path, username=None, hidden=False):
    path = expand_windows_var(path, username).replace('\\', '/').replace('//', '/')
    if username:
        home = get_homedir(username)
        path = str(Path(home) / path.replace(home, '').lstrip('/'))
    return hidden_target(path, hidden, keep_dot=True)
