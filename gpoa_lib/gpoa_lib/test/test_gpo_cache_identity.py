import unittest
from types import SimpleNamespace
from unittest.mock import patch
from gpoa_lib.storage.dconf_registry import Dconf_registry, extract_display_name_version, gpo_cache_key, add_to_dict


class CacheIdentityTest(unittest.TestCase):
    def test_source_survives_metadata_roundtrip(self):
        info = SimpleNamespace(counter=1, name='11111111-1111-1111-1111-111111111111', display_name='policy', version=1, cache_source='example')
        with patch.object(Dconf_registry, 'global_registry_dict', {}), patch.object(Dconf_registry, '_force', False):
            add_to_dict('/snapshot', None, info)
            cache = extract_display_name_version(Dconf_registry.global_registry_dict, None)
            self.assertEqual(cache[gpo_cache_key(info.name, 'example')]['correct_path'], '/snapshot')

    def test_equal_names_do_not_alias_and_legacy_entries_miss(self):
        a, b = '11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222'
        prefix = Dconf_registry._GpoPriority
        entries = {
            prefix + '/1': dict(name=a, display_name='same', version='1', correct_path='/a', cache_source='EXAMPLE'),
            prefix + '/2': dict(name=b, display_name='same', version='1', correct_path='/b', cache_source='EXAMPLE'),
            prefix + '/3': dict(display_name='legacy', version='1', correct_path='/bad'),
        }
        with patch.object(Dconf_registry, '_force', False), patch.object(Dconf_registry, 'get_info', return_value='example'):
            cache = extract_display_name_version(entries, 'user')
            self.assertEqual(cache[gpo_cache_key(a)]['correct_path'], '/a')
            self.assertEqual(cache[gpo_cache_key(b)]['correct_path'], '/b')
            self.assertEqual(len(cache), 2)
            self.assertNotIn(gpo_cache_key(a, 'other'), cache)
            entries[prefix + '/1']['display_name'] = 'renamed'
            self.assertEqual(extract_display_name_version(entries, 'user'), cache)
