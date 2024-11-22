#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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
import signal

from .arguments import ExitCodeUpdater
from .kerberos import machine_kdestroy

def signal_handler(sig_number, frame):
    print('Received signal, exiting gracefully')
    # Ignore extra signals
    signal.signal(sig_number, signal.SIG_IGN)

    # Kerberos cache cleanup on interrupt
    machine_kdestroy()

    os._exit(ExitCodeUpdater.EXIT_SIGINT)

