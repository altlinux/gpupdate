import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from gpoa_lib.util.dbus import print_dbus_result


class CliStatusTest(unittest.TestCase):
    def test_reply_status(self):
        with patch('builtins.print'):
            self.assertEqual(7, print_dbus_result((7, 'failure', '')))
            self.assertEqual(0, print_dbus_result((0, '', '')))
        for reply in (None, (), ('invalid',)):
            with self.assertRaises((ValueError, TypeError)):
                print_dbus_result(reply)

    def test_all_targets_run_and_failures_are_distinguished(self):
        loader = SourceFileLoader('gpupdate_cli_test', str(Path(__file__).parents[1] / 'gpupdate'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cli = importlib.util.module_from_spec(spec)
        loader.exec_module(cli)
        for error, expected in ((None, 4), (RuntimeError('transport'), 2)):
            first, second = Mock(), Mock()
            first.run.return_value = 7
            first.run.side_effect = error
            second.run.return_value = 0
            self.assertEqual(expected, cli.run_appliers((first, second)))
            second.run.assert_called_once_with()
        self.assertEqual(0, cli.run_appliers((None, Mock(run=Mock(return_value=0)))))
