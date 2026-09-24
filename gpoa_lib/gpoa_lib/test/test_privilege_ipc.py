import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from gpoa_lib.util.system import _write_child_result


class PrivilegeIPCTests(unittest.TestCase):
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
        self.assertEqual(b''.join(chunks), b'{"key": "value"}')
