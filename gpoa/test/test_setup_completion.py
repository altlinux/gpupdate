import argparse
import ast
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
BASH_COMPLETION = Path('/usr/share/bash-completion/bash_completion')


@unittest.skipUnless(shutil.which('bash'), 'Bash is required')
class SetupCompletionTests(unittest.TestCase):
    def complete(self, words, native=False):
        script = r'''
if [[ $2 == native ]]; then
    source /usr/share/bash-completion/bash_completion
else
    _init_completion() {
        COMPREPLY=()
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
        cur=${words[cword]}
        prev=${words[cword-1]}
        split=false
        if [[ $cur == --*=* ]]; then
            prev=${cur%%=*}
            cur=${cur#*=}
            split=true
        fi
    }
fi
source "$1"
shift 2
gpupdate-setup() {
    if [[ $# != 1 || $1 != list ]]; then
        printf 'Unexpected setup action: %s\n' "$*" >&2
        exit 99
    fi
    printf '%s\n' workstation server 'custom profile'
}
COMP_WORDS=("$@")
COMP_CWORD=$((${#COMP_WORDS[@]} - 1))
COMP_LINE=""
for ((i = 0; i < ${#COMP_WORDS[@]}; i++)); do
    word=${COMP_WORDS[i]}
    if [[ $word == = || ( $i -gt 0 && ${COMP_WORDS[i-1]} == = ) ]]; then
        COMP_LINE+="$word"
    else
        COMP_LINE+="${COMP_LINE:+ }$word"
    fi
done
COMP_POINT=${#COMP_LINE}
_gpupdate-setup "${COMP_WORDS[0]}" "${COMP_WORDS[COMP_CWORD]}" "${COMP_WORDS[COMP_CWORD-1]}"
printf '%s\n' "${COMPREPLY[@]}"
'''
        result = subprocess.run(
            ['bash', '--noprofile', '--norc', '-c', script, 'completion-test',
             str(ROOT / 'completions/gpupdate-setup'),
             'native' if native else 'stub', *words],
            capture_output=True, text=True, timeout=10, check=True)
        self.assertEqual(result.stderr, '')
        return [line for line in result.stdout.splitlines() if line]

    def test_subcommands_and_help_only_at_the_command_position(self):
        self.assertIn('enable', self.complete(['gpupdate-setup', '']))
        self.assertEqual(self.complete(['gpupdate-setup', 'set-b']), ['set-backend'])
        for action in ('list', 'list-backends', 'status', 'disable',
                       'default-policy', 'active-policy', 'active-backend'):
            with self.subTest(action=action):
                self.assertEqual(self.complete(['gpupdate-setup', action, '']),
                                 ['--help', '-h'])
                self.assertEqual(self.complete(['gpupdate-setup', action, '--help', '']), [])

    def test_help_option_prefix_at_root_and_after_each_subcommand(self):
        actions = ('', 'list', 'list-backends', 'status', 'enable', 'disable',
                   'update', 'write', 'set-backend', 'default-policy',
                   'active-policy', 'active-backend')
        for action in actions:
            command = ['gpupdate-setup'] + ([action] if action else [])
            for prefix in ('--h', '--he', '--hel'):
                with self.subTest(action=action, prefix=prefix):
                    self.assertEqual(self.complete(command + [prefix]), ['--help'])
                    if BASH_COMPLETION.is_file():
                        self.assertEqual(self.complete(command + [prefix], native=True),
                                         ['--help'])

    def test_enable_update_complete_option_names_and_values(self):
        for action in ('enable', 'update'):
            with self.subTest(action=action):
                prefix = ['gpupdate-setup', action]
                self.assertEqual(self.complete(prefix + ['--b']), ['--backend'])
                self.assertEqual(self.complete(prefix + ['--l']), ['--local-policy'])
                self.assertEqual(self.complete(prefix + ['--backend', '']),
                                 ['local', 'samba', 'freeipa'])
                self.assertEqual(self.complete(prefix + ['--backend', 'fre']), ['freeipa'])
                self.assertEqual(self.complete(prefix + ['--backend=fre']), ['freeipa'])
                self.assertEqual(self.complete(prefix + ['--unknown=value']), [])
                self.assertEqual(self.complete(prefix + ['--help', '']), [])

    def test_policy_values_and_option_order(self):
        for action in ('enable', 'update'):
            with self.subTest(action=action):
                prefix = ['gpupdate-setup', action]
                self.assertEqual(self.complete(prefix + ['--local-policy', '']),
                                 ['workstation', 'server', 'custom profile'])
                self.assertEqual(self.complete(prefix + ['--local-policy=cus']),
                                 ['custom profile'])
                self.assertEqual(self.complete(prefix + [
                    '--local-policy', 'workstation', '--backend', 'fre']), ['freeipa'])
                self.assertEqual(self.complete(prefix + [
                    '--backend', 'freeipa', '--local-policy', 'wor']), ['workstation'])

    def test_positional_backend_and_write_arguments(self):
        self.assertEqual(self.complete(['gpupdate-setup', 'set-backend', '']),
                         ['local', 'samba', 'freeipa'])
        self.assertEqual(self.complete(['gpupdate-setup', 'set-backend', 'fre']), ['freeipa'])
        self.assertEqual(self.complete(['gpupdate-setup', 'set-backend', 'freeipa', '']), [])
        self.assertEqual(self.complete(['gpupdate-setup', 'write', '']), ['enable', 'disable'])
        for status in ('enable', 'disable'):
            prefix = ['gpupdate-setup', 'write', status]
            self.assertEqual(self.complete(prefix + ['wor']), ['workstation'])
            self.assertEqual(self.complete(prefix + ['workstation', 'fre']), ['freeipa'])
            self.assertEqual(self.complete(prefix + ['workstation', 'freeipa', '']), [])
            self.assertEqual(self.complete(prefix + ['--help', '']), [])

    def test_backend_candidates_match_the_actual_cli(self):
        source = ROOT / 'gpoa/gpupdate-setup'
        tree = ast.parse(source.read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'parse_arguments')
        namespace = {'argparse': argparse}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), namespace)
        for backend in self.complete(['gpupdate-setup', 'set-backend', '']):
            for arguments in (['enable', '--backend', backend],
                              ['update', '--backend', backend],
                              ['set-backend', backend],
                              ['write', 'enable', 'workstation', backend]):
                with self.subTest(arguments=arguments), patch.object(
                        sys, 'argv', ['gpupdate-setup', *arguments]):
                    self.assertEqual(namespace['parse_arguments']().backend, backend)

    @unittest.skipUnless(BASH_COMPLETION.is_file(), 'bash-completion is required')
    def test_native_bash_completion_with_split_equals_words(self):
        for action in ('enable', 'update'):
            prefix = ['gpupdate-setup', action]
            self.assertEqual(self.complete(prefix + ['--b'], native=True), ['--backend'])
            self.assertEqual(self.complete(prefix + ['--backend', 'fre'], native=True), ['freeipa'])
            self.assertEqual(self.complete(prefix + ['--backend=fre'], native=True), ['freeipa'])
            self.assertEqual(self.complete(prefix + ['--backend', '=', 'fre'], native=True), ['freeipa'])
            self.assertEqual(self.complete(prefix + ['--backend', '=', ''], native=True),
                             ['local', 'samba', 'freeipa'])
            self.assertEqual(self.complete(prefix + ['--local-policy', '=', 'wor'], native=True),
                             ['workstation'])


if __name__ == '__main__':
    unittest.main()
