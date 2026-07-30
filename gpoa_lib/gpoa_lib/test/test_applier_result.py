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

import unittest

from gpoa_lib.applier_result import (
    ApplierResult,
    ItemStatus,
    STATUS_APPLIED,
    STATUS_PARTIAL,
    STATUS_SKIPPED,
    STATUS_FAILED,
    STATUS_NOT_IMPLEMENTED,
    RESULT_SUCCESS,
    RESULT_FAILED,
    RESULT_SKIPPED,
)


class ItemStatusTestCase(unittest.TestCase):

    def test_create(self):
        item = ItemStatus(key='sshd-gssapi-auth', action='set', result=RESULT_SUCCESS)
        self.assertEqual(item.key, 'sshd-gssapi-auth')
        self.assertEqual(item.action, 'set')
        self.assertEqual(item.result, RESULT_SUCCESS)
        self.assertEqual(item.detail, '')

    def test_create_with_detail(self):
        item = ItemStatus(key='unit', action='create', result=RESULT_FAILED, detail='exit code 1')
        self.assertEqual(item.detail, 'exit code 1')

    def test_to_dict(self):
        item = ItemStatus(key='k', action='a', result='r', detail='d')
        d = item.to_dict()
        self.assertEqual(d['key'], 'k')
        self.assertEqual(d['action'], 'a')
        self.assertEqual(d['result'], 'r')
        self.assertEqual(d['detail'], 'd')


class ApplierResultTestCase(unittest.TestCase):

    def test_create_applied(self):
        result = ApplierResult(name='control', status=STATUS_APPLIED)
        self.assertEqual(result.name, 'control')
        self.assertEqual(result.status, STATUS_APPLIED)
        self.assertEqual(result.items, [])
        self.assertIsNone(result.error)

    def test_factory_applied(self):
        items = [
            ItemStatus('key1', 'set', RESULT_SUCCESS),
            ItemStatus('key2', 'set', RESULT_SUCCESS),
        ]
        result = ApplierResult.applied('control', items)
        self.assertEqual(result.status, STATUS_APPLIED)
        self.assertEqual(len(result.items), 2)

    def test_factory_not_implemented(self):
        result = ApplierResult.not_implemented('package')
        self.assertEqual(result.status, STATUS_NOT_IMPLEMENTED)
        self.assertEqual(result.items, [])

    def test_factory_skipped(self):
        result = ApplierResult.skipped('ntp', 'disabled')
        self.assertEqual(result.status, STATUS_SKIPPED)
        self.assertEqual(result.error, 'disabled')

    def test_factory_failed(self):
        result = ApplierResult.failed('cifs', 'mount error')
        self.assertEqual(result.status, STATUS_FAILED)
        self.assertEqual(result.error, 'mount error')

    def test_counts(self):
        items = [
            ItemStatus('a', 'set', RESULT_SUCCESS),
            ItemStatus('b', 'set', RESULT_SUCCESS),
            ItemStatus('c', 'set', RESULT_FAILED),
            ItemStatus('d', 'skip', RESULT_SKIPPED),
        ]
        result = ApplierResult(name='test', status=STATUS_PARTIAL, items=items)
        self.assertEqual(result.applied_count, 2)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.skipped_count, 1)

    def test_counts_empty(self):
        result = ApplierResult(name='test', status=STATUS_SKIPPED)
        self.assertEqual(result.applied_count, 0)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.skipped_count, 0)

    def test_to_dict(self):
        items = [ItemStatus('k', 'set', RESULT_SUCCESS)]
        result = ApplierResult(name='ctrl', status=STATUS_APPLIED, items=items, metadata={'foo': 'bar'})
        d = result.to_dict()
        self.assertEqual(d['name'], 'ctrl')
        self.assertEqual(d['status'], STATUS_APPLIED)
        self.assertEqual(d['applied_count'], 1)
        self.assertEqual(d['failed_count'], 0)
        self.assertEqual(d['skipped_count'], 0)
        self.assertEqual(len(d['items']), 1)
        self.assertEqual(d['items'][0]['key'], 'k')
        self.assertEqual(d['metadata'], {'foo': 'bar'})

    def test_repr_with_items(self):
        items = [ItemStatus('a', 'set', RESULT_SUCCESS), ItemStatus('b', 'set', RESULT_FAILED)]
        result = ApplierResult(name='test', status=STATUS_PARTIAL, items=items)
        r = repr(result)
        self.assertIn('test', r)
        self.assertIn('partial', r)
        self.assertIn('applied=1', r)
        self.assertIn('failed=1', r)

    def test_repr_without_items(self):
        result = ApplierResult.not_implemented('package')
        r = repr(result)
        self.assertIn('package', r)
        self.assertIn('not_implemented', r)

    def test_metadata_default(self):
        result = ApplierResult(name='x', status=STATUS_APPLIED)
        self.assertEqual(result.metadata, {})


class ImportTestCase(unittest.TestCase):

    def test_import_from_top_level(self):
        from gpoa_lib import ApplierResult, ItemStatus
        self.assertIsNotNone(ApplierResult)
        self.assertIsNotNone(ItemStatus)


if __name__ == '__main__':
    unittest.main()
