import subprocess
import sys
import unittest

from gpoa_lib.util.kerberos import _wait_process


class KerberosTimeoutTests(unittest.TestCase):
    def test_timeout_kills_and_reaps_process(self):
        with subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']) as process:
            with self.assertRaises(subprocess.TimeoutExpired):
                _wait_process(process, 0.05)
            self.assertIsNotNone(process.poll())

    def test_cancellation_kills_and_reaps_process(self):
        with subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']) as process:
            with self.assertRaises(InterruptedError):
                _wait_process(process, 15, cancelled=lambda: True)
            self.assertIsNotNone(process.poll())
