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


import sys


def geterr():
    '''
    Fetches information about recent exception so we will be able
    to print tracebacks and other information in a uniform way.
    '''
    etype, evalue, etrace = sys.exc_info()

    traceinfo = dict({
          'file': etrace.tb_frame.f_code.co_filename
        , 'line': etrace.tb_lineno
        , 'name': etrace.tb_frame.f_code.co_name
        , 'type': etype.__name__
        , 'message': evalue
    })

    del(etype, evalue, etrace)

    return traceinfo

class NotUNCPathError(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return self.path

class GetGPOListFail(Exception):
    def __init__(self, exc):
        self.exc = exc

    def __str__(self):
        return self.exc

