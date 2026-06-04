#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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


class Result:
    '''
    Type-safe return wrapper for gpoa_lib operations.

    Uses the same pattern as ``Result`` in Rust / ``Result`` in Go:
    successful operations carry ``data``, failed ones carry ``error``.

    Usage
    -----
    ::

        result = runner.run('control')
        if result:
            print('OK:', result.data)
        else:
            print('Error:', result.error)

        # Or use class methods:
        ok_result = Result.ok_result({'applied': 3})
        err_result = Result.fail('Database not found')
    '''

    def __init__(self, ok, data=None, error=None):
        self.ok = ok
        self.data = data
        self.error = error

    def __bool__(self):
        return self.ok

    def __repr__(self):
        if self.ok:
            return f'Result(ok=True, data={self.data!r})'
        return f'Result(ok=False, error={self.error!r})'

    @classmethod
    def ok_result(cls, data=None):
        '''
        Create a successful result.

        Parameters
        ----------
        data : any, optional
            Payload to carry.

        Returns
        -------
        Result
        '''
        return cls(True, data=data)

    @classmethod
    def fail(cls, error):
        '''
        Create a failed result.

        Parameters
        ----------
        error : str or Exception
            Error description.

        Returns
        -------
        Result
        '''
        return cls(False, error=str(error))
