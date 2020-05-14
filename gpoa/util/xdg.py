#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
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


from configparser import RawConfigParser, DEFAULTSECT
import os
from xdg.BaseDirectory import xdg_config_home


from .users import with_privileges


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

def xdg_get_desktop_user(username):
    if not username:
        name = 'root'
        desktop_full_path = with_privileges(name, xdg_get_desktop)
        return '/etc/skel/{}'.format(desktop_full_path.rpartition('/')[2])

    return xdg_get_desktop()

def xdg_get_desktop():
    stream = os.popen('source /etc/locale.conf; xdg-user-dir DESKTOP')
    output = stream.read()[:-1]
    print(output)
    return output

