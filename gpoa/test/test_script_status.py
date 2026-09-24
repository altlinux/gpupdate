import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


class ScriptStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        loader = SourceFileLoader('script_status_test', str(Path(__file__).parents[1] / 'scripts_runner'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        cls.module = importlib.util.module_from_spec(spec)
        loader.exec_module(cls.module)

    def test_failure_does_not_prevent_later_script(self):
        runner = self.module.Scripts_runner.__new__(self.module.Scripts_runner)
        runner.failed = 0
        with patch.object(self.module.subprocess, 'run', side_effect=[
                Mock(returncode=9), FileNotFoundError('missing'), Mock(returncode=0)]) as run:
            self.assertIn('status 9', runner.run_cmd_subprocess(['first']))
            self.assertIn('failed', runner.run_cmd_subprocess(['missing']))
            self.assertIn('Script run', runner.run_cmd_subprocess(['last']))
        self.assertEqual(3, run.call_count)
        self.assertEqual(2, runner.failed)

    def test_strict_status_is_opt_in(self):
        with patch.object(self.module, 'wait_for_process'), patch.object(
                self.module, 'Scripts_runner', return_value=Mock(failed=1)):
            self.assertEqual(0, self.module.main([]))
            self.assertEqual(1, self.module.main(['--fail-on-error']))
