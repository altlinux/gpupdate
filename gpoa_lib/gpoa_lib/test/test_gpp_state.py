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
from unittest.mock import patch, MagicMock

from gpoa_lib.storage.gpp_state import (
    find_removed_elements,
    find_gpo_removed_elements,
    get_element_type_name,
    is_element_applied,
    mark_element_applied,
    GppStateManager,
    CLEANUP_SKIP_ACTIONS,
)


class FindRemovedElementsTestCase(unittest.TestCase):

    def test_removed_element_returned(self):
        current = [{'uid': 'a', 'remove_policy': True}]
        previous = [{'uid': 'a', 'remove_policy': True}, {'uid': 'b', 'remove_policy': True}]
        result = find_removed_elements(current, previous)
        uids = [e['uid'] for e in result]
        self.assertIn('b', uids)

    def test_nothing_removed(self):
        current = [{'uid': 'a'}, {'uid': 'b'}]
        previous = [{'uid': 'a'}, {'uid': 'b'}]
        result = find_removed_elements(current, previous)
        self.assertEqual(len(result), 0)

    def test_remove_policy_false_not_returned(self):
        current = [{'uid': 'a'}]
        previous = [{'uid': 'a'}, {'uid': 'b', 'remove_policy': False}]
        result = find_removed_elements(current, previous)
        self.assertEqual(len(result), 0)

    def test_custom_key_field(self):
        current = [{'name': 'a'}]
        previous = [{'name': 'a'}, {'name': 'b', 'remove_policy': True}]
        result = find_removed_elements(current, previous, key_field='name')
        self.assertEqual(len(result), 1)


class FindGpoRemovedElementsTestCase(unittest.TestCase):

    def test_unlinked_gpo(self):
        current_gpos = {'{GUID-1}'}
        previous = [
            {'policy_guid': '{GUID-1}'},
            {'policy_guid': '{GUID-2}', 'remove_policy': True},
        ]
        result = find_gpo_removed_elements(current_gpos, previous)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['policy_guid'], '{GUID-2}')

    def test_all_linked(self):
        current_gpos = {'{GUID-1}', '{GUID-2}'}
        previous = [
            {'policy_guid': '{GUID-1}'},
            {'policy_guid': '{GUID-2}'},
        ]
        result = find_gpo_removed_elements(current_gpos, previous)
        self.assertEqual(len(result), 0)


class GetElementTypeNameTestCase(unittest.TestCase):

    def test_known_type(self):
        obj = type('Ini_file', (), {})()
        result = get_element_type_name(obj)
        self.assertIsNotNone(result)

    def test_unknown_type_returns_class_name(self):
        obj = type('CompletelyUnknownType', (), {})()
        result = get_element_type_name(obj)
        self.assertEqual(result, 'CompletelyUnknownType')


class IsElementAppliedTestCase(unittest.TestCase):

    @patch('gpoa_lib.storage.gpp_state.get_previous_elements')
    def test_already_applied(self, mock_prev):
        mock_prev.return_value = [{'uid': 'test-1', 'applied': '2026-01-01'}]
        element = {'uid': 'test-1', 'apply_once': True}
        self.assertTrue(is_element_applied(element, 'Files'))

    @patch('gpoa_lib.storage.gpp_state.get_previous_elements')
    def test_not_applied(self, mock_prev):
        mock_prev.return_value = []
        element = {'uid': 'test-1', 'apply_once': True}
        self.assertFalse(is_element_applied(element, 'Files'))

    @patch('gpoa_lib.storage.gpp_state.get_previous_elements')
    def test_no_apply_once_flag(self, mock_prev):
        element = {'uid': 'test-1'}
        self.assertFalse(is_element_applied(element, 'Files'))


class MarkElementAppliedTestCase(unittest.TestCase):

    def test_sets_applied(self):
        element = {'uid': 'test-1'}
        mark_element_applied(element, 'Files')
        self.assertIn('applied', element)

    def test_sets_on_object(self):
        obj = MagicMock()
        element = {'uid': 'test-1'}
        mark_element_applied(element, 'Files', element_obj=obj)
        self.assertIn('applied', element)
        obj.__setattr__('applied', element['applied'])


class GppStateManagerTestCase(unittest.TestCase):

    @patch('gpoa_lib.storage.gpp_state.get_current_gpo_guids')
    def test_should_skip_not_applied(self, mock_gpos):
        mock_gpos.return_value = set()
        sm = GppStateManager()
        sm._previous_elements = {}
        element = {'uid': 'test-1'}
        self.assertFalse(sm.should_skip(element, 'Files'))

    @patch('gpoa_lib.storage.gpp_state.get_current_gpo_guids')
    @patch('gpoa_lib.storage.gpp_state.is_element_applied')
    def test_should_skip_applied(self, mock_applied, mock_gpos):
        mock_gpos.return_value = set()
        mock_applied.return_value = True
        sm = GppStateManager()
        sm._previous_elements = {}
        element = {'uid': 'test-1'}
        self.assertTrue(sm.should_skip(element, 'Files'))

    @patch('gpoa_lib.storage.gpp_state.get_current_gpo_guids')
    def test_cleanup_removed_calls_handler(self, mock_gpos):
        mock_gpos.return_value = set()
        sm = GppStateManager()
        handler = MagicMock()
        current = [{'uid': 'a'}]
        with patch.object(sm, 'find_removed', return_value=[{'uid': 'b', 'action': 'C'}]):
            sm.cleanup_removed('Files', current, handler)
        handler.assert_called_once()

    @patch('gpoa_lib.storage.gpp_state.get_current_gpo_guids')
    def test_cleanup_skip_delete_action(self, mock_gpos):
        mock_gpos.return_value = set()
        sm = GppStateManager()
        handler = MagicMock()
        current = [{'uid': 'a'}]
        with patch.object(sm, 'find_removed', return_value=[{'uid': 'b', 'action': 'D'}]):
            sm.cleanup_removed('Files', current, handler)
        handler.assert_not_called()


class CleanupSkipActionsTestCase(unittest.TestCase):

    def test_delete_in_skip_set(self):
        self.assertIn('D', CLEANUP_SKIP_ACTIONS)
        self.assertIn('DELETE', CLEANUP_SKIP_ACTIONS)

    def test_create_not_in_skip_set(self):
        self.assertNotIn('C', CLEANUP_SKIP_ACTIONS)
