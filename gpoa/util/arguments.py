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

import logging
import logging.handlers
from enum import IntEnum

from messages import message_with_code
from .logging import slogm


def set_loglevel(loglevel_num=None):
    '''
    Set the log level global value.
    '''
    format_message = '%(message)s'
    formatter = logging.Formatter(format_message)
    loglevels = ['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'FATAL']
    log_num = loglevel_num
    log_level = 10

    # A little bit of defensive programming
    if not log_num:
        log_num = 1
    if log_num < 0:
        log_num = 0
    if log_num > 5:
        log_num = 5

    log_level = 10 * log_num

    logging.basicConfig(format=format_message)
    logger = logging.getLogger()
    logger.setLevel(log_level)

    log_stdout = logging.StreamHandler()
    log_stdout.setLevel(log_level)
    log_stdout.setFormatter(formatter)

    log_syslog = logging.handlers.SysLogHandler()
    log_syslog.setLevel(logging.DEBUG)
    log_syslog.setFormatter(formatter)

    logger.handlers = [log_stdout, log_syslog]


def process_target(target_name=None):
    '''
    The target may be 'All', 'Computer' or 'User'. This function
    determines which one was specified.
    '''
    target = 'All'

    if target_name == 'Computer':
        target = 'Computer'

    if target_name == 'User':
        target = 'User'

    logdata = dict({'target': target})
    logging.debug(slogm(message_with_code('I3'), logdata))

    return target

class ExitCodeUpdater(IntEnum):
    '''
    Exit code contract for gpupdate application
    '''
    EXIT_SUCCESS = 0
    FAIL_NO_RUNNER = 1
    FAIL_GPUPDATE_COMPUTER_NOREPLY = 2
    FAIL_GPUPDATE_USER_NOREPLY = 3
    EXIT_SIGINT = 130

