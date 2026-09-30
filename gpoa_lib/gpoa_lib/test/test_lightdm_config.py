import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from configobj import ConfigObjError
from gpoa_lib.frontend_plugins.dm_applier import DMApplier
from gpoa_lib.util.gpoa_ini_parsing import GpoaConfigObj


class LightDMConfigTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plugin = DMApplier.__new__(DMApplier)
        self.plugin.log = Mock()
        self.plugin.backup = False
        self.plugin.dm_config = {'Greeter.Background': '/images/My picture.png'}
        self.layers = [self.root / name for name in ('vendor', 'local', 'xdg', 'etc')]
        for directory in self.layers:
            directory.mkdir()
        self.plugin.LIGHTDM_CONFIG_DIRS = tuple(map(str, self.layers))
        self.plugin.LIGHTDM_CONFIG_FILE = str(self.root / 'lightdm.conf')
        self.desktops = [self.root / 'greeters', self.root / 'xgreeters']
        for directory in self.desktops:
            directory.mkdir()
        self.plugin.LIGHTDM_GREETER_DIRS = tuple(map(str, self.desktops))

    def desktop(self, directory, name, command):
        path = directory / (name + '.desktop')
        path.write_text('[Desktop Entry]\nType=Application\nExec=' + command + '\n')
        return path

    def read_ini(self, path):
        return self.plugin._read_lightdm_conf(str(path))

    def test_primary_detection_does_not_confuse_fallback_or_non_seat_keys(self):
        target = self.desktop(self.desktops[0], 'lightdm-kde-greeter',
                              'env QT_WAYLAND_SHELL_INTEGRATION=layer-shell kwin_wayland --exit-with-session lightdm-kde-greeter')
        (self.desktops[0] / 'lightdm-default-greeter.desktop').symlink_to(target)
        (self.layers[-1] / '90-fallback.conf').write_text(
            '[Seat:*]\ngreeter-session-fallback=lightdm-kde-greeter-x11\n'
            '[LightDM]\ngreeter-session=slick-greeter\n')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), 'lightdm-kde-greeter')
        Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text(
            '[Seat:*]\ngreeter-session=lightdm-kde-greeter-x11\n')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), 'lightdm-kde-greeter-x11')

    def test_layer_filename_and_main_file_precedence(self):
        for directory, name in zip(self.layers, ('lightdm-gtk-greeter', 'slick-greeter',
                                                 'lightdm-kde-greeter', 'slick-greeter')):
            (directory / '10-greeter.conf').write_text('[Seat:*]\ngreeter-session=' + name + '\n')
        (self.layers[-1] / '90-greeter.conf').write_text(
            '[Seat:*]\ngreeter-session=lightdm-kde-greeter-x11\n')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), 'lightdm-kde-greeter-x11')
        Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text('[Seat:*]\ngreeter-session=lightdm-gtk-greeter\n')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), 'lightdm-gtk-greeter')

    def test_desktop_alias_and_arguments_are_read_not_executed(self):
        self.desktop(self.desktops[1], 'lightdm-default-greeter',
                     '/usr/sbin/lightdm-gtk-greeter --example')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), 'lightdm-gtk-greeter')
        self.desktop(self.desktops[1], 'custom', '/usr/sbin/slick-greeter --example')
        Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text('[Seat:*]\ngreeter-session=custom\n')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), 'slick-greeter')

    def test_glib_ini_does_not_inherit_python_default_section(self):
        self.desktop(self.desktops[0], 'lightdm-default-greeter', '/usr/sbin/slick-greeter')
        Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text(
            '[DEFAULT]\ngreeter-session=lightdm-gtk-greeter\n[Seat:*]\ngreeter-hide-users=true\n')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), 'slick-greeter')

    def test_unknown_missing_malformed_and_conflicting_seats_do_not_write(self):
        for content in ('[Seat:*]\ngreeter-session=web-greeter\n',
                        '[Seat:*]\ngreeter-session=\n',
                        '[Seat:*]\ngreeter-session=slick-greeter\n[Seat:seat1]\ngreeter-session=lightdm-gtk-greeter\n',
                        ''):
            Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text(content)
            with patch.object(self.plugin, 'generate_lightdm') as write:
                self.assertFalse(self.plugin.write_config('lightdm', str(self.root / 'output')))
                write.assert_not_called()
                self.assertFalse((self.root / 'output').exists())
        Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text('not an ini file\n')
        with self.assertRaises(ConfigObjError):
            self.plugin._detect_lightdm_greeter()

    def test_native_output_repairs_old_quotes_and_preserves_settings_and_comments(self):
        path = self.root / '50-custom.conf'
        path.write_text('# administrator comment\n["Seat:*"]\n'
                        '"greeter-background" = "/old/image.jpg"\n'
                        '"greeter-hide-users" = "true"\n'
                        '# session comment\n"user-session" = "plasma"\n'
                        'empty-value =\n[LightDM]\nminimum-vt = 1\n')
        path.chmod(0o640)
        original_owner = (path.stat().st_uid, path.stat().st_gid)
        self.assertIsNotNone(self.plugin.generate_lightdm(str(path)))
        conf = self.read_ini(path)
        self.assertEqual(conf['Seat:*']['greeter-background'], '/images/My picture.png')
        self.assertEqual(conf['Seat:*']['greeter-hide-users'], 'true')
        self.assertEqual(conf['Seat:*']['user-session'], 'plasma')
        self.assertEqual(conf['Seat:*']['empty-value'], '')
        self.assertEqual(conf['LightDM']['minimum-vt'], '1')
        text = path.read_text()
        self.assertIn('# administrator comment', text)
        self.assertIn('# session comment', text)
        self.assertNotIn('["Seat:*"]', text)
        self.assertIn('greeter-background = /images/My picture.png', text)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertEqual((path.stat().st_uid, path.stat().st_gid), original_owner)
        self.plugin.generate_lightdm(str(path))
        self.assertEqual(path.read_text(), text)

    def test_supported_families_share_correct_files_and_preserve_theme_choices(self):
        for name, (_, section, key) in DMApplier.LIGHTDM_GREETER_CONFIGS.items():
            with self.subTest(greeter=name):
                path = self.root / (name + '.conf')
                path.write_text('# theme comment\n[greeter]\ntheme-name=userbar\n'
                                '[Greeter]\ndraw-user-backgrounds=true\n'
                                '[lightdm_theme_userbar]\nBackgroundFillMode=2\n')
                self.plugin.LIGHTDM_GREETER_CONFIGS = {name: (str(path), section, key)}
                self.assertTrue(self.plugin._generate_lightdm_greeter_config(name))
                conf = self.read_ini(path)
                self.assertEqual(conf[section][key], self.plugin.dm_config['Greeter.Background'])
                self.assertEqual(conf['greeter']['theme-name'], 'userbar')
                self.assertEqual(conf['Greeter']['draw-user-backgrounds'], 'true')
                self.assertEqual(conf['lightdm_theme_userbar']['BackgroundFillMode'], '2')
        self.assertEqual(DMApplier.LIGHTDM_GREETER_CONFIGS['lightdm-kde-greeter'],
                         DMApplier.LIGHTDM_GREETER_CONFIGS['lightdm-kde-greeter-x11'])

    def test_native_paths_keep_commas_hashes_semicolons_percent_and_unicode(self):
        self.plugin.dm_config['Greeter.Background'] = '/images/Фон #1;2, 100%.png'
        path = self.root / '50-custom.conf'
        for _ in range(2):
            self.plugin.generate_lightdm(str(path))
            self.assertEqual(self.read_ini(path)['Seat:*']['greeter-background'],
                             self.plugin.dm_config['Greeter.Background'])

    def test_failed_publication_leaves_original_and_symlink_intact(self):
        path = self.root / '50-custom.conf'
        original = '[Seat:*]\ngreeter-background=/old.jpg\n'
        path.write_text(original)
        alias = self.root / 'linked.conf'
        alias.symlink_to(path)
        with patch('gpoa_lib.frontend_plugins.dm_applier.os.replace', side_effect=OSError('disk error')):
            self.assertIsNone(self.plugin.generate_lightdm(str(alias)))
        self.assertEqual(path.read_text(), original)
        self.assertTrue(alias.is_symlink())
        self.assertEqual(list(self.root.glob('.gpupdate-*')), [])
        self.plugin.generate_lightdm(str(alias))
        self.assertTrue(alias.is_symlink())
        self.assertEqual(self.read_ini(path)['Seat:*']['greeter-background'],
                         self.plugin.dm_config['Greeter.Background'])

    def test_injected_multiline_value_does_not_replace_original(self):
        path = self.root / '50-custom.conf'
        path.write_text('[Seat:*]\ngreeter-hide-users=true\n')
        self.plugin.dm_config['Greeter.Background'] = '/image.png\nautologin-user=test'
        self.assertIsNone(self.plugin.generate_lightdm(str(path)))
        self.assertEqual(path.read_text(), '[Seat:*]\ngreeter-hide-users=true\n')

    def test_duplicate_native_groups_and_keys_merge_last_values(self):
        Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text(
            '[Seat:*]\ngreeter-session=lightdm-gtk-greeter\n'
            'greeter-session=slick-greeter\n'
            '[LightDM]\nminimum-vt=1\n'
            '[Seat:*]\ngreeter-session=lightdm-kde-greeter-x11\n')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), 'lightdm-kde-greeter-x11')
        self.assertEqual(self.read_ini(self.plugin.LIGHTDM_CONFIG_FILE)['LightDM']['minimum-vt'], '1')

    def test_existing_gpoa_parser_still_rejects_duplicates_by_default(self):
        for content in ('[group]\nkey=first\nkey=last\n', '[group]\nkey=first\n[group]\nother=last\n'):
            with self.assertRaises(ConfigObjError):
                GpoaConfigObj(content.splitlines(), list_values=False)

    def test_literal_read_does_not_activate_invalid_quoted_sections_keys_or_values(self):
        self.desktop(self.desktops[0], 'lightdm-default-greeter', '/usr/sbin/slick-greeter')
        for content in ('["Seat:*"]\ngreeter-session=lightdm-gtk-greeter\n',
                        '[Seat:*]\n"greeter-session"=lightdm-gtk-greeter\n'):
            Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text(content)
            self.assertEqual(self.plugin._detect_lightdm_greeter(), 'slick-greeter')
        Path(self.plugin.LIGHTDM_CONFIG_FILE).write_text('[Seat:*]\ngreeter-session="lightdm-gtk-greeter"\n')
        self.assertEqual(self.plugin._detect_lightdm_greeter(), '"lightdm-gtk-greeter"')
        with patch.object(self.plugin, 'generate_lightdm') as write:
            self.assertFalse(self.plugin.write_config('lightdm', str(self.root / 'output')))
            write.assert_not_called()


if __name__ == '__main__':
    unittest.main()
