#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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
import subprocess
from functools import lru_cache

from messages import message_with_code

from .logging import log
from .util import get_homedir


def _get_system_lang():
    try:
        out = subprocess.check_output(['localectl', 'status'], text=True)
        for line in out.splitlines():
            if 'System Locale' in line:
                return line.split('LANG=', 1)[1].strip()
    except Exception:
        return None


@lru_cache(maxsize=32)
def xdg_get_desktop(username, homedir = None):
    if username:
        homedir = get_homedir(username)
    if not homedir:
        msgtext = message_with_code('E18')
        logdata = {}
        log('E18', logdata)
        raise Exception(msgtext)

    user_dirs_conf = os.path.join(homedir, '.config', 'user-dirs.dirs')
    if not os.path.exists(user_dirs_conf):
        lang = _get_system_lang()
        if lang and not lang.startswith('C'):
            os.popen(
                'export HOME={home}; export LANG={lang}; export LC_ALL={lang}; '
                'xdg-user-dirs-update'.format(home=homedir, lang=lang)
            ).read()

    stream = os.popen('export HOME={}; xdg-user-dir DESKTOP'.format(homedir))
    output = stream.read()[:-1]
    return output