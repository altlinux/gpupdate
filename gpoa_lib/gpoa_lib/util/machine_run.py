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


def run(command, backend, config_dir='/run'):
    original_cache = os.environ.get('KRB5CCNAME')
    runtime_dir = tempfile.mkdtemp(prefix='gpupdate-machine-', dir=config_dir)
    cache_path = os.path.join(runtime_dir, 'krb5cc')
    child = None
    interrupted = None

    def forward_signal(signum, _frame):
        nonlocal interrupted
        interrupted = signum
        if child is not None and child.poll() is None:
            child.send_signal(signum)

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
        child = subprocess.Popen(command, env=child_env)
        return_code = child.wait()
        if interrupted is not None:
            return_code = 128 + interrupted
        return return_code
    finally:
        for signum, handler in signal_handlers.items():
            signal.signal(signum, handler)
        if child is not None and child.poll() is None:
            child.terminate()
            child.wait()
        _destroy_cache(cache_path)
        shutil.rmtree(runtime_dir, ignore_errors=True)
        if original_cache is None:
            os.environ.pop('KRB5CCNAME', None)
        else:
            os.environ['KRB5CCNAME'] = original_cache


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
