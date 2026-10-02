import os
import signal
import unittest
from unittest.mock import patch

from gpoa_lib.util import kerberos, signals


class CacheOwnershipTests(unittest.TestCase):
    def test_client_interrupt_never_destroys_session_cache(self):
        for cache in ('FILE:/session/cache', 'KCM:1000', 'KEYRING:persistent:1000'):
            with patch.dict(os.environ, KRB5CCNAME=cache), \
                    patch.object(kerberos, '_owned_caches', set()), \
                    patch.object(kerberos, 'machine_kdestroy') as destroy, \
                    patch.object(signals.signal, 'signal'), \
                    patch.object(signals.os, '_exit', side_effect=SystemExit):
                with self.assertRaises(SystemExit):
                    signals.signal_handler(signal.SIGINT, None)
                destroy.assert_not_called()

    def test_engine_cleans_own_cache_not_inherited_cache(self):
        caches = {(os.getpid(), '/owned/cache'), (os.getpid() + 1, '/other/cache')}
        with patch.object(kerberos, '_owned_caches', caches), \
                patch.object(kerberos, 'machine_kdestroy') as destroy:
            kerberos.destroy_owned_machine_caches()
        destroy.assert_called_once_with('/owned/cache')

    def test_missing_owned_cache_never_falls_back_to_caller_cache(self):
        with patch.dict('os.environ', {'KRB5CCNAME': 'FILE:/caller-cache'}), \
                patch.object(kerberos.subprocess, 'Popen'), \
                patch.object(kerberos, '_wait_process'), \
                patch.object(kerberos.os.path, 'exists', side_effect=lambda path: path == '/caller-cache'), \
                patch.object(kerberos.os, 'unlink') as unlink:
            kerberos.machine_kdestroy('/already-destroyed-owned-cache')
            unlink.assert_not_called()

    def test_explicit_cleanup_needs_no_machine_name_and_unlinks_on_failure(self):
        owned = '/owned/cache'
        with patch.dict('os.environ', {'KRB5CCNAME': 'FILE:/caller-cache'}), \
                patch.object(kerberos, '_owned_caches', {(os.getpid(), owned)}) as caches, \
                patch.object(kerberos, 'get_machine_name', side_effect=AssertionError('unexpected lookup')), \
                patch.object(kerberos.subprocess, 'Popen', side_effect=OSError('kdestroy unavailable')), \
                patch.object(kerberos.os.path, 'exists', return_value=True), \
                patch.object(kerberos.os, 'unlink') as unlink:
            with self.assertRaisesRegex(OSError, 'kdestroy unavailable'):
                kerberos.machine_kdestroy(owned)
            unlink.assert_called_once_with(owned)
            self.assertEqual(set(), caches)
