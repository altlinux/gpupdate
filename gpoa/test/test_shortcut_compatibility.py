import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from frontend import shortcut_applier as shortcuts
from gpt.shortcuts import shortcut, TargetType


class ShortcutCompatibilityTest(unittest.TestCase):
    def test_machine_fields_and_url_type_survive_reconstruction(self):
        values = dict(dest='%DesktopDir%/link', path='https://example.org', arguments='',
                      name='Example', action='U', type='URL', icon='browser', comment='Description',
                      uid='uid', policy_guid='policy', disabled=True, remove_policy=True,
                      apply_once=True, bypass_errors=True, applied='machine-stamp',
                      filters=[{'FilterComputer': {'name': 'client', 'negate': False, 'bool': 'AND'}}])
        obj = shortcut.from_machine_dict(values)
        for name in ('dest', 'icon', 'comment', 'uid', 'policy_guid', 'disabled',
                     'remove_policy', 'apply_once', 'bypass_errors'):
            self.assertEqual(getattr(obj, name), values[name])
        self.assertTrue(obj.is_usercontext())
        self.assertFalse(hasattr(obj, 'applied'))
        self.assertEqual(dict(obj)['filters'], values['filters'])
        entry = obj.desktop()
        self.assertEqual(entry.get('Type'), 'Link')
        self.assertEqual(entry.get('Icon'), 'browser')
        # File-system shortcuts also retain their descriptions in the output.
        obj.set_type(TargetType.FILESYSTEM)
        self.assertEqual(obj.desktop().get('Comment'), 'Description')

    def test_merge_evaluates_restored_filters(self):
        obj = shortcuts.shortcut_applier_user.__new__(shortcuts.shortcut_applier_user)
        obj.username = 'user'
        obj.storage = Mock()
        obj.storage.get_dictionary_from_dconf_file_db.return_value = {
            'Software/BaseALT/Policies/Preferences/Machine': {'Shortcuts': str([
                dict(dest='link', path='/usr/bin/true', name='link', action='C',
                     filters=[{'FilterComputer': {'name': 'other-client'}}])])}}
        with patch.object(shortcuts, '_filter_objects', return_value=[]) as filter_objects:
            self.assertEqual(obj.get_machine_shortcuts(), [])
            self.assertTrue(filter_objects.call_args.args[0][0].filters)
            self.assertEqual(filter_objects.call_args.args[1], 'user')

    def test_create_update_replace_trust_final_content_but_not_noop_create(self):
        with tempfile.TemporaryDirectory() as home, \
                patch.object(shortcuts, 'get_homedir', return_value=home), \
                patch.object(shortcuts, 'homedir_exists', return_value=True), \
                patch.object(shortcuts, 'get_user_info', return_value=SimpleNamespace(pw_uid=os.geteuid())), \
                patch.object(shortcuts, 'expand_windows_var', side_effect=lambda value, user: value.replace('%HOME%', home)), \
                patch.object(shortcuts.shutil, 'which', return_value='/usr/bin/gio'), \
                patch.object(shortcuts.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')) as run:
            obj = shortcut('link', '/usr/bin/true', '', 'Link', 'C')
            path = Path(home, 'link.desktop')
            for action in ('C', 'U', 'R'):
                obj.action = action
                obj.comment = action
                run.reset_mock()
                shortcuts.apply_shortcut(obj, 'user')
                self.assertEqual(run.call_count, 2)
                self.assertEqual(run.call_args.args[0][-2:],
                                 ['metadata::xfce-exe-checksum', hashlib.sha256(path.read_bytes()).hexdigest()])
                self.assertTrue(path.stat().st_mode & 0o100)
            path.write_text('[Desktop Entry]\nExec=modified\n')
            obj.action = 'C'
            run.reset_mock()
            shortcuts.apply_shortcut(obj, 'user')
            run.assert_not_called()
            self.assertIn('modified', path.read_text())
            obj.action = 'D'
            shortcuts.apply_shortcut(obj, 'user')
            run.assert_not_called()
            self.assertFalse(path.exists())

    def test_metadata_failure_is_optional_and_does_not_stop_other_backend(self):
        with tempfile.TemporaryDirectory() as home, \
                patch.object(shortcuts, 'get_homedir', return_value=home), \
                patch.object(shortcuts, 'get_user_info', return_value=SimpleNamespace(pw_uid=os.geteuid())), \
                patch.object(shortcuts.shutil, 'which', return_value='gio'), \
                patch.object(shortcuts.subprocess, 'run', side_effect=OSError('no metadata service')) as run:
            path = Path(home, 'link.desktop')
            path.write_text('content')
            shortcuts.mark_shortcut_trusted(str(path), 'user')
            self.assertEqual(run.call_count, 2)
            self.assertEqual(path.read_text(), 'content')

    def test_root_pass_does_not_set_another_users_metadata(self):
        with patch.object(shortcuts, 'get_user_info', return_value=SimpleNamespace(pw_uid=os.geteuid() + 1)), \
                patch.object(shortcuts.subprocess, 'run') as run:
            shortcuts.mark_shortcut_trusted('/home/user/link.desktop', 'user')
            run.assert_not_called()
