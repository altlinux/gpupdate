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

from enum import Enum, IntEnum
import logging
import logging.handlers

from .logging import log


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

    target = "All"
    if target_name:
        target = target_name

    logdata = {'target': target}
    log('D10', logdata)

    return target.upper()

class ExitCodeUpdater(IntEnum):
    '''
    Exit code contract for gpupdate application
    '''
    EXIT_SUCCESS = 0
    FAIL_NO_RUNNER = 1
    FAIL_GPUPDATE_COMPUTER_NOREPLY = 2
    FAIL_GPUPDATE_USER_NOREPLY = 3
    EXIT_SIGINT = 130

class FileAction(Enum):
    CREATE = 'C'
    REPLACE = 'R'
    UPDATE = 'U'
    DELETE = 'D'

    def __str__(self):
        return self.value

def action_letter2enum(letter):
    if letter in ['C', 'R', 'U', 'D']:
        if letter == 'C': return FileAction.CREATE
        if letter == 'R': return FileAction.REPLACE
        if letter == 'U': return FileAction.UPDATE
        if letter == 'D': return FileAction.DELETE

    return FileAction.CREATE
