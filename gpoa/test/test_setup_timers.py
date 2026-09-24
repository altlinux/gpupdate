import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


class SetupTimersTest(unittest.TestCase):
    def test_only_timers_in_existing_managers_are_stopped(self):
        loader = SourceFileLoader('setup_timers_test', str(Path(__file__).parents[1] / 'gpupdate-setup'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        with patch.object(module, 'runcmd', side_effect=[(0, ''), (0,
                'user@1001.service loaded active running User Manager\n'
                'user@1002.service loaded active running User Manager\n')]) as command, \
                patch.object(module.pwd, 'getpwuid', return_value=Mock(
                    pw_gid=100, pw_name='alice', pw_dir='/home/alice')), \
                patch.object(module.os.path, 'exists', return_value=True), \
                patch.object(module.subprocess, 'run') as run:
            self.assertEqual([], module.stop_policy_timers())
        self.assertEqual(2, run.call_count)
        for call in run.call_args_list:
            self.assertEqual(['/bin/systemctl', '--user', 'stop', 'gpupdate-user.timer'], call.args[0])
            self.assertNotIn('KRB5CCNAME', call.kwargs['env'])
        self.assertEqual(['/bin/systemctl', 'stop', 'gpupdate.timer'], command.call_args_list[0].args[0])
