#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from .config import GPConfig
from .kerberos import machine_kinit, forget_machine_cache


def _destroy_cache(cache_path):
    forget_machine_cache(cache_path)
    try:
        subprocess.run(
            ['kdestroy', '-c', cache_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        os.unlink(cache_path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _parse_arguments(argv):
    parser = argparse.ArgumentParser(
        description='Run a command with a temporary machine Kerberos credential cache',
    )
    parser.add_argument('--config', help='gpupdate configuration file')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command and args.command[0] == '--':
        args.command = args.command[1:]
    if not args.command:
        parser.error('a command is required')
    return args


def _signal_group(child, signum):
    try:
        os.killpg(child.pid, signum)
    except ProcessLookupError:
        pass


def _stop_process_group(child, grace=3):
    # Descendants inherit this owned session. Stop them before destroying its
    # credentials, even if the immediate shell has already exited.
    _signal_group(child, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        child.poll()
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    _signal_group(child, signal.SIGKILL)
    child.wait(timeout=3)
    deadline = time.monotonic() + 3
    while _group_has_live_members(child.pid):
        if time.monotonic() >= deadline:
            raise RuntimeError('Command group did not stop after SIGKILL')
        time.sleep(0.02)


def _group_has_live_members(group):
    for name in os.listdir('/proc'):
        if not name.isdecimal():
            continue
        try:
            with open('/proc/{}/stat'.format(name)) as stream:
                fields = stream.read().rsplit(') ', 1)[1].split()
            if int(fields[2]) == group and fields[0] not in ('Z', 'X'):
                return True
        except (OSError, ValueError, IndexError):
            continue
    return False


def run(command, backend, config_dir='/run'):
    original_cache = os.environ.get('KRB5CCNAME')
    runtime_dir = tempfile.mkdtemp(prefix='gpupdate-machine-', dir=config_dir)
    cache_path = os.path.join(runtime_dir, 'krb5cc')
    child = None
    interrupted = None

    def forward_signal(signum, _frame):
        nonlocal interrupted
        interrupted = signum
        if child is not None:
            _signal_group(child, signum)

    handled_signals = [signal.SIGINT, signal.SIGTERM]
    if hasattr(signal, 'SIGHUP'):
        handled_signals.append(signal.SIGHUP)
    signal_handlers = {
        signum: signal.signal(signum, forward_signal)
        for signum in handled_signals
    }

    try:
        os.environ['KRB5CCNAME'] = 'FILE:{}'.format(cache_path)
        try:
            acquired = machine_kinit(cache_path, backend, cancelled=lambda: interrupted is not None)
        except InterruptedError:
            if interrupted is None:
                raise
            return 128 + interrupted
        if interrupted is not None:
            return 128 + interrupted
        if not acquired:
            raise RuntimeError('unable to obtain machine Kerberos credentials')

        child_env = os.environ.copy()
        child_env['KRB5CCNAME'] = 'FILE:{}'.format(cache_path)
        child = subprocess.Popen(command, env=child_env, start_new_session=True)
        while True:
            if interrupted is not None:
                return_code = 128 + interrupted
                break
            try:
                return_code = child.wait(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                continue
        if interrupted is not None:
            return_code = 128 + interrupted
        elif return_code < 0:
            return_code = 128 - return_code
        return return_code
    finally:
        try:
            if child is not None:
                _stop_process_group(child)
        finally:
            child = None
            _destroy_cache(cache_path)
            shutil.rmtree(runtime_dir, ignore_errors=True)
            if original_cache is None:
                os.environ.pop('KRB5CCNAME', None)
            else:
                os.environ['KRB5CCNAME'] = original_cache
            for signum, handler in signal_handlers.items():
                signal.signal(signum, handler)


def main(argv=None):
    args = _parse_arguments(argv)
    if os.geteuid() != 0:
        print('gpupdate-machine-run must be executed as root', file=sys.stderr)
        return 1

    config = GPConfig(args.config)
    try:
        return run(args.command, config.get_backend())
    except Exception as exc:
        print('gpupdate-machine-run: {}'.format(exc), file=sys.stderr)
        return 1
