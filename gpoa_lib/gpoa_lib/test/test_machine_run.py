#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#

import os
import signal
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from gpoa_lib.util import machine_run as gpupdate_machine_run


class MachineRunTestCase(unittest.TestCase):
    def test_command_arguments(self):
        args = gpupdate_machine_run._parse_arguments(
            ['--', 'smbclient', '-k', '//server/share'],
        )
        self.assertEqual(args.command, ['smbclient', '-k', '//server/share'])

    @patch('gpoa_lib.util.machine_run.machine_kinit', return_value=True)
    @patch('gpoa_lib.util.machine_run._destroy_cache')
    @patch('gpoa_lib.util.machine_run.subprocess.Popen')
    def test_cache_is_private_to_child_and_cleaned(self, popen, destroy_cache, kinit):
        process = MagicMock()
        process.wait.return_value = 7
        process.poll.return_value = 7
        popen.return_value = process

        with tempfile.TemporaryDirectory() as runtime_dir:
            old_cache = os.environ.get('KRB5CCNAME')
            os.environ['KRB5CCNAME'] = 'FILE:/old/cache'
            try:
                result = gpupdate_machine_run.run(
                    ['smbclient', '-k'], 'samba', runtime_dir,
                )
            finally:
                if old_cache is None:
                    os.environ.pop('KRB5CCNAME', None)
                else:
                    os.environ['KRB5CCNAME'] = old_cache

        self.assertEqual(result, 7)
        kinit.assert_called_once()
        child_env = popen.call_args.kwargs['env']
        self.assertTrue(child_env['KRB5CCNAME'].startswith('FILE:'))
        self.assertEqual(os.environ.get('KRB5CCNAME'), old_cache)
        destroy_cache.assert_called_once_with(kinit.call_args.args[0])

    @patch('gpoa_lib.util.machine_run.machine_kinit', return_value=True)
    @patch('gpoa_lib.util.machine_run._destroy_cache')
    @patch('gpoa_lib.util.machine_run.subprocess.Popen')
    def test_signal_returns_shell_exit_code(self, popen, _destroy_cache, _kinit):
        handlers = {}
        process = MagicMock()

        def wait():
            handlers[signal.SIGTERM](signal.SIGTERM, None)
            return -signal.SIGTERM

        process.wait.side_effect = wait
        process.poll.side_effect = [None, -signal.SIGTERM]
        popen.return_value = process

        def set_signal(signum, handler):
            previous = handlers.get(signum, signal.SIG_DFL)
            handlers[signum] = handler
            return previous

        with tempfile.TemporaryDirectory() as runtime_dir:
            with patch(
                'gpoa_lib.util.machine_run.signal.signal',
                side_effect=set_signal,
            ):
                result = gpupdate_machine_run.run(
                    ['command'], 'samba', runtime_dir,
                )

        self.assertEqual(result, 128 + signal.SIGTERM)
        process.send_signal.assert_called_once_with(signal.SIGTERM)
