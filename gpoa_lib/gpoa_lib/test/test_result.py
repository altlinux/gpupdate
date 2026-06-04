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

import unittest

from gpoa_lib.result import Result


class ResultOkTestCase(unittest.TestCase):

    def test_ok_result_with_data(self):
        r = Result.ok_result({'key': 'value'})
        self.assertTrue(r)
        self.assertEqual(r.data, {'key': 'value'})

    def test_ok_result_no_data(self):
        r = Result.ok_result()
        self.assertTrue(r)
        self.assertIsNone(r.data)

    def test_ok_result_with_none_data(self):
        r = Result.ok_result(None)
        self.assertTrue(r)
        self.assertIsNone(r.data)

    def test_ok_result_with_list(self):
        r = Result.ok_result([1, 2, 3])
        self.assertEqual(r.data, [1, 2, 3])

    def test_ok_result_error_is_none(self):
        r = Result.ok_result(42)
        self.assertIsNone(r.error)


class ResultFailTestCase(unittest.TestCase):

    def test_fail_with_string(self):
        r = Result.fail('something broke')
        self.assertFalse(r)
        self.assertEqual(r.error, 'something broke')

    def test_fail_with_exception(self):
        r = Result.fail(RuntimeError('disk full'))
        self.assertFalse(r)
        self.assertIn('disk full', r.error)

    def test_fail_data_is_none(self):
        r = Result.fail('error')
        self.assertIsNone(r.data)

    def test_fail_with_empty_string(self):
        r = Result.fail('')
        self.assertFalse(r)
        self.assertEqual(r.error, '')


class ResultBoolTestCase(unittest.TestCase):

    def test_ok_is_truthy(self):
        r = Result.ok_result(1)
        self.assertTrue(r)
        if r:
            pass
        else:
            self.fail('ok result should be truthy')

    def test_fail_is_falsy(self):
        r = Result.fail('bad')
        self.assertFalse(r)
        if not r:
            pass
        else:
            self.fail('fail result should be falsy')


class ResultReprTestCase(unittest.TestCase):

    def test_repr_ok_with_data(self):
        r = Result.ok_result(42)
        text = repr(r)
        self.assertIn('ok=True', text)
        self.assertIn('42', text)

    def test_repr_ok_without_data(self):
        r = Result.ok_result()
        text = repr(r)
        self.assertIn('ok=True', text)

    def test_repr_fail(self):
        r = Result.fail('oops')
        text = repr(r)
        self.assertIn('ok=False', text)
        self.assertIn('oops', text)


class ResultConstructorTestCase(unittest.TestCase):

    def test_direct_constructor_ok(self):
        r = Result(True, data='payload')
        self.assertTrue(r.ok)
        self.assertEqual(r.data, 'payload')

    def test_direct_constructor_fail(self):
        r = Result(False, error='broken')
        self.assertFalse(r.ok)
        self.assertEqual(r.error, 'broken')

    def test_attributes_writable(self):
        r = Result.ok_result(10)
        r.data = 20
        self.assertEqual(r.data, 20)
