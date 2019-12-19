import subprocess

from configparser import RawConfigParser, DEFAULTSECT
import os
from xdg.BaseDirectory import xdg_config_home

def get_user_dir(dir_name, default=None):
    '''
    Get path to XDG's user directory
    '''
    config = RawConfigParser(allow_no_value=True)
    userdirs_path = os.path.join(xdg_config_home, 'user-dirs.dirs')
    try:
        with open(userdirs_path, 'r') as f:
            config.read_string('[DEFAULT]\n' + f.read())
        return config.get(DEFAULTSECT, 'XDG_DESKTOP_DIR')
    except Exception as exc:
        return default

