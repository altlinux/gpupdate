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

from __future__ import annotations

from dataclasses import dataclass, field


STATUS_APPLIED = 'applied'
STATUS_PARTIAL = 'partial'
STATUS_SKIPPED = 'skipped'
STATUS_FAILED = 'failed'
STATUS_NOT_IMPLEMENTED = 'not_implemented'

RESULT_SUCCESS = 'success'
RESULT_FAILED = 'failed'
RESULT_SKIPPED = 'skipped'


@dataclass
class ItemStatus:
    '''
    Status of a single item processed by an applier.

    Attributes
    ----------
    key : str
        Registry path, file path, unit name, or other item identifier.
    action : str
        What was done: ``'set'``, ``'create'``, ``'delete'``, ``'skip'``, ``'copy'``.
    result : str
        Outcome: ``'success'``, ``'failed'``, ``'skipped'``.
    detail : str
        Additional information (exit code, error message, etc.).
    '''
    key: str
    action: str
    result: str
    detail: str = ''

    def to_dict(self):
        return {
            'key': self.key,
            'action': self.action,
            'result': self.result,
            'detail': self.detail,
        }


@dataclass
class ApplierResult:
    '''
    Execution status returned by an applier or plugin.

    Attributes
    ----------
    name : str
        Applier or plugin name (e.g. ``'control'``, ``'cifs'``).
    status : str
        Overall status: ``'applied'``, ``'partial'``, ``'skipped'``,
        ``'failed'``, ``'not_implemented'``.
    items : list[ItemStatus]
        Per-item details. May be empty for stub results.
    error : str or None
        Error message when ``status`` is ``'failed'``.
    metadata : dict
        Arbitrary extra information (e.g. file counts, timing).
    '''
    name: str
    status: str
    items: list = field(default_factory=list)
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def applied_count(self):
        '''Number of successfully applied items.'''
        return sum(1 for i in self.items if i.result == RESULT_SUCCESS)

    @property
    def failed_count(self):
        '''Number of failed items.'''
        return sum(1 for i in self.items if i.result == RESULT_FAILED)

    @property
    def skipped_count(self):
        '''Number of skipped items.'''
        return sum(1 for i in self.items if i.result == RESULT_SKIPPED)

    def to_dict(self):
        '''Serialize to a plain dict for JSON reporting.'''
        return {
            'name': self.name,
            'status': self.status,
            'error': self.error,
            'applied_count': self.applied_count,
            'failed_count': self.failed_count,
            'skipped_count': self.skipped_count,
            'items': [i.to_dict() for i in self.items],
            'metadata': self.metadata,
        }

    def __repr__(self):
        if self.items:
            return (f'ApplierResult({self.name!r}, {self.status!r}, '
                    f'applied={self.applied_count}, '
                    f'failed={self.failed_count}, '
                    f'skipped={self.skipped_count})')
        return f'ApplierResult({self.name!r}, {self.status!r})'

    @classmethod
    def not_implemented(cls, name):
        '''Create a stub result for appliers that do not track status.'''
        return cls(name=name, status=STATUS_NOT_IMPLEMENTED)

    @classmethod
    def skipped(cls, name, reason=''):
        '''Create a result for a disabled or empty applier.'''
        return cls(name=name, status=STATUS_SKIPPED, error=reason)

    @classmethod
    def failed(cls, name, error):
        '''Create a result for a critically failed applier.'''
        return cls(name=name, status=STATUS_FAILED, error=error)

    @classmethod
    def applied(cls, name, items=None):
        '''Create a result for a successfully applied applier.'''
        return cls(name=name, status=STATUS_APPLIED, items=items or [])
