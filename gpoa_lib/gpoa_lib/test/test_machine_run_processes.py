import subprocess
import sys
from unittest import TestCase


class MachineRunProcessTest(TestCase):
    def test_signal_resistant_command_group_is_stopped_before_cache_cleanup(self):
        code = r'''
import ctypes, os, signal, sys, tempfile, threading, time
from pathlib import Path
from unittest.mock import patch
from gpoa_lib.util import machine_run
ctypes.CDLL(None).prctl(36, 1, 0, 0, 0)
with tempfile.TemporaryDirectory() as directory:
    pids = Path(directory) / 'pids'
    child_code = """
import os, signal, subprocess, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
descendant = subprocess.Popen([sys.executable, '-c', 'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)'])
open(sys.argv[1], 'w').write(str(os.getpid()) + ' ' + str(descendant.pid))
time.sleep(30)
"""
    def cancel():
        deadline = time.monotonic() + 5
        while not pids.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        time.sleep(.1)
        os.kill(os.getpid(), signal.SIGTERM)
    thread = threading.Thread(target=cancel)
    thread.start()
    def cleanup(cache):
        for pid in map(int, pids.read_text().split()):
            try:
                state = Path('/proc', str(pid), 'stat').read_text().split(') ')[1].split()[0]
            except FileNotFoundError:
                continue
            assert state == 'Z', (pid, state)
    with patch.object(machine_run, 'machine_kinit', return_value=True), patch.object(machine_run, '_destroy_cache', side_effect=cleanup):
        assert machine_run.run([sys.executable, '-c', child_code, str(pids)], 'samba', directory) == 143
    thread.join()
    for pid in map(int, pids.read_text().split()):
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
'''
        subprocess.run([sys.executable, '-B', '-c', code], check=True, timeout=15)
