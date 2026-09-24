import unittest
from unittest.mock import Mock, patch
from backend.freeipa_backend import freeipa_backend


class FreeIPARetrievalTests(unittest.TestCase):
    def make_backend(self, machine=True):
        obj = freeipa_backend.__new__(freeipa_backend)
        obj._freeipa_backend__kinit_successful = False
        obj._is_machine_username = machine
        obj.username = 'user'
        obj.storage = Mock()
        obj.ipacreds = Mock()
        return obj

    def test_chain_failure_propagates_before_application(self):
        for machine in (True, False):
            obj = self.make_backend(machine)
            obj.ipacreds.update_gpos.side_effect = RuntimeError('offline')
            with patch('backend.freeipa_backend.Dconf_registry'), patch('backend.freeipa_backend.get_uid_by_username'), \
                    patch('backend.freeipa_backend.get_local_gpt') as local:
                with self.assertRaisesRegex(RuntimeError, 'offline'):
                    obj.retrieve_and_store()
                local.assert_not_called()

    def test_successful_empty_chain_still_uses_local_policy(self):
        obj = self.make_backend()
        obj.ipacreds.update_gpos.return_value = ([], 'ipa.example')
        with patch('backend.freeipa_backend.get_local_gpt', return_value='local'):
            self.assertEqual(obj._get_gpts('host'), ['local'])
