import json
from pathlib import Path
import shutil
import subprocess
import unittest

from jinja2 import Environment, FileSystemLoader


class UserRuleScopeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'JavaScript runtime required')
    def test_every_action_is_scoped_to_user(self):
        templates = Path(__file__).resolve().parents[3] / 'gpoa' / 'templates'
        template = Environment(loader=FileSystemLoader(str(templates))).get_template(
            '48-alt_group_policy_permissions_user.rules.j2')
        verdicts = ('No', 'Yes', 'Auth_self', 'Auth_admin', 'Auth_self_keep', 'Auth_admin_keep')
        for verdict in verdicts:
            for count in (1, 2, 3):
                with self.subTest(verdict=verdict, count=count):
                    actions = ['test.action{}'.format(i) for i in range(count)]
                    values = {key: [] for key in verdicts}
                    values.update(User='alice')
                    values[verdict] = actions
                    source = 'const rules=[]; const polkit={addRule:r=>rules.push(r),Result:'
                    source += json.dumps({v.upper(): v for v in verdicts}) + '};\n'
                    source += template.render(**values)
                    source += '\nconst actions=' + json.dumps(actions + ['unrelated']) + ';'
                    source += '''
console.log(JSON.stringify(['alice','bob'].map(user =>
    actions.map(id => rules.map(r => r({id}, {user}) ?? null)))));
'''
                    output = subprocess.check_output(['node', '-e', source], text=True, timeout=10)
                    self.assertEqual(json.loads(output), [
                        [[verdict]] * count + [[None]], [[None]] * (count + 1)])
