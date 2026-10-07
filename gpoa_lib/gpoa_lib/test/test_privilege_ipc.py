import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from gpoa_lib.util.system import _write_child_result


class PrivilegeIPCTests(unittest.TestCase):
    def test_worker_cleanup_and_failures_never_resume_parent_code(self):
        code = '''
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from gpoa_lib.util import system
origin = os.getpid()
proc = MagicMock()
proc.__enter__.return_value.stdout = [b'DBUS_SESSION_BUS_PID=12345\\n']
user = SimpleNamespace(pw_uid=1000, pw_gid=1000, pw_dir='/tmp')
with patch.object(system.os, 'getuid', return_value=0), \\
     patch.object(system, 'get_user_info', return_value=user), \\
     patch.object(system.os, 'getgrouplist', return_value=[1000]), \\
     patch.object(system, 'set_privileges'), \\
     patch.object(system.subprocess, 'Popen', return_value=proc), \\
     patch.object(system.os, 'kill', side_effect=ProcessLookupError), \\
     patch.object(system, 'dbus_session', side_effect=RuntimeError):
    assert system.with_privileges('alice', lambda: {'ok': True}) == {'ok': True}
    for failure in (RuntimeError('callback failed'), SystemExit(0)):
        def callback():
            raise failure
        try:
            system.with_privileges('alice', callback)
        except RuntimeError:
            pass
        else:
            raise AssertionError('failed worker was reported successful')
    try:
        system.with_privileges('alice', lambda: object())
    except RuntimeError:
        pass
    else:
        raise AssertionError('unserializable result reported successful')
assert os.getpid() == origin
print('parent completed')
'''
        result = subprocess.run([sys.executable, '-B', '-c', code], text=True,
                                capture_output=True, check=True, timeout=15)
        self.assertEqual(result.stdout.strip(), 'parent completed')

    def test_large_result_round_trip_without_deadlock(self):
        code = '''
import os
from gpoa_lib.util.system import _read_child_result, _write_child_result
for value in (None, {}, {'items': ['значение' * 100] * 3000}):
    rfd, wfd = os.pipe()
    pid = os.fork()
    if not pid:
        os.close(rfd)
        _write_child_result(wfd, value)
        os.close(wfd)
        os._exit(0)
    os.close(wfd)
    assert _read_child_result(pid, rfd) == value
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass
    else:
        raise AssertionError('child was not reaped')
'''
        subprocess.run([sys.executable, '-B', '-c', code], check=True, timeout=15)

    def test_partial_writes_are_completed(self):
        chunks = []
        def write(fd, data):
            chunks.append(bytes(data[:3]))
            return len(chunks[-1])
        with patch('gpoa_lib.util.system.os.write', side_effect=write):
            _write_child_result(1, {'key': 'value'})
        payload = b'{"key": "value"}'
        self.assertEqual(b''.join(chunks), len(payload).to_bytes(8, 'big') + payload)

    def test_result_does_not_wait_for_fork_descendant_eof(self):
        code = '''
import os, signal, time, ctypes
from gpoa_lib.util.system import _read_child_result, _write_child_result
ctypes.CDLL(None).prctl(36, 1, 0, 0, 0)
rfd, wfd = os.pipe()
pid = os.fork()
if not pid:
    os.close(rfd)
    descendant = os.fork()
    if not descendant:
        time.sleep(30)
        os._exit(0)
    _write_child_result(wfd, {'descendant': descendant})
    os._exit(0)
os.close(wfd)
started = time.monotonic()
result = _read_child_result(pid, rfd)
assert time.monotonic() - started < 2
os.kill(result['descendant'], signal.SIGKILL)
os.waitpid(result['descendant'], 0)
'''
        subprocess.run([sys.executable, '-B', '-c', code], check=True, timeout=10)
