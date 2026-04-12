#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import tempfile
import unittest
import unittest.mock
import ast
import base64
import types
from enum import Enum, unique
from pathlib import Path


class _storage_stub:
    def __init__(self):
        self.items = []

    def add_systemd(self, item, policy_name):
        item.policy_name = policy_name
        self.items.append(item)

def _load_gpt_discovery_helpers():
    source_path = os.path.join(os.getcwd(), 'gpt', 'gpt.py')
    with open(source_path, 'r', encoding='utf-8') as file_obj:
        tree = ast.parse(file_obj.read(), filename=source_path)

    needed_names = {
        'FileType',
        'get_preftype',
        'find_dir',
        'find_file',
        'find_preferences',
        'find_preffile',
    }
    selected_nodes = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in needed_names:
            selected_nodes.append(node)
        elif isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if any(name in needed_names for name in targets):
                selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {
        'Enum': Enum,
        'unique': unique,
        'os': os,
        'Path': Path,
    }
    exec(compile(module, source_path, 'exec'), namespace)
    return types.SimpleNamespace(**namespace)


class GptSystemdsTestCase(unittest.TestCase):
    def _path(self, filename):
        return '{}/test/gpt/data/{}'.format(os.getcwd(), filename)

    def test_read_systemds_all_types(self):
        import gpt.systemds

        items = gpt.systemds.read_systemds(self._path('Systemds.xml'))
        self.assertEqual(len(items), 11)
        self.assertEqual(items[0].unit, 'sshd.service')
        self.assertEqual(items[0].state, 'enable')
        self.assertEqual(items[0].apply_mode, 'always')
        self.assertEqual(items[0].policy_target, 'machine')
        self.assertEqual(items[0].edit_mode, 'create_or_override')
        self.assertEqual(items[0].dropin_name, 'override.conf')
        self.assertEqual(items[0].unit_file_mode, 'text')
        self.assertEqual(
            base64.b64decode(items[0].unit_file_b64.encode('ascii')).decode('utf-8'),
            items[0].unit_file,
        )
        self.assertEqual(len(items[0].file_dependencies), 2)

        # Ensure automatic suffix mapping works for all supported tags.
        expected_suffixes = {
            'service': '.service',
            'socket': '.socket',
            'timer': '.timer',
            'path': '.path',
            'mount': '.mount',
            'automount': '.automount',
            'swap': '.swap',
            'target': '.target',
            'device': '.device',
            'slice': '.slice',
            'scope': '.scope',
        }
        for item in items:
            self.assertTrue(item.unit.endswith(expected_suffixes[item.element_type]))

    def test_soft_validation_skips_invalid_entries(self):
        import gpt.systemds

        items = gpt.systemds.read_systemds(self._path('Systemds_invalid.xml'))
        # good + bad-dep (kept with filtered deps); invalid path values are skipped
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].unit, 'good.service')
        self.assertEqual(items[1].unit, 'bad3.service')
        self.assertEqual(items[1].file_dependencies, [])
        units = {item.unit for item in items}
        self.assertNotIn('../../tmp/evil.service', units)
        self.assertNotIn('safe.service', units)

    def test_merge_systemds(self):
        import gpt.systemds

        storage = _storage_stub()
        items = gpt.systemds.read_systemds(self._path('Systemds.xml'))
        gpt.systemds.merge_systemds(storage, items, 'policy-test')
        self.assertEqual(len(storage.items), len(items))
        self.assertEqual(storage.items[0].policy_name, 'policy-test')

    def test_read_systemds_preserves_quotes_via_unit_file_b64(self):
        import gpt.systemds

        unit_file_text = "[Service]\nExecStart=/bin/bash -c \"echo 'ok'\"\n"
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<Systemds clsid="{{ROOT}}" disabled="0">
  <Service clsid="{{C1}}" name="quoted" uid="{{U1}}">
    <Properties unit="quoted" state="as_is">
      <UnitFile mode="text">{}</UnitFile>
    </Properties>
  </Service>
</Systemds>
""".format(unit_file_text)

        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.xml', delete=False) as file_obj:
            file_obj.write(xml_content)
            tmp_path = file_obj.name

        try:
            items = gpt.systemds.read_systemds(tmp_path)
        finally:
            os.unlink(tmp_path)

        self.assertEqual(len(items), 1)
        restored = base64.b64decode(items[0].unit_file_b64.encode('ascii')).decode('utf-8')
        self.assertEqual(restored, unit_file_text)

    def test_read_systemds_rejects_invalid_dependency_path(self):
        import gpt.systemds

        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<Systemds clsid="{{ROOT}}" disabled="0">
  <Service clsid="{{C1}}" name="dep" uid="{{U1}}">
    <Properties unit="dep" state="as_is">
      <FileDependencies>
        <Dependency mode="changed" path="../relative"/>
      </FileDependencies>
    </Properties>
  </Service>
</Systemds>
"""
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.xml', delete=False) as file_obj:
            file_obj.write(xml_content)
            tmp_path = file_obj.name

        try:
            items = gpt.systemds.read_systemds(tmp_path)
        finally:
            os.unlink(tmp_path)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].file_dependencies, [])

    def test_read_systemds_rejects_oversized_unit_file(self):
        import gpt.systemds

        unit_file_text = "A" * (gpt.systemds.MAX_UNIT_FILE_SIZE + 1)
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<Systemds clsid="{{ROOT}}" disabled="0">
  <Service clsid="{{C1}}" name="big" uid="{{U1}}">
    <Properties unit="big" state="as_is">
      <UnitFile mode="text">{}</UnitFile>
    </Properties>
  </Service>
</Systemds>
""".format(unit_file_text)
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.xml', delete=False) as file_obj:
            file_obj.write(xml_content)
            tmp_path = file_obj.name

        try:
            items = gpt.systemds.read_systemds(tmp_path)
        finally:
            os.unlink(tmp_path)

        self.assertEqual(items, [])

    def test_gpt_discovery_supports_windows_systemd_layout(self):
        gpt_helpers = _load_gpt_discovery_helpers()

        with tempfile.TemporaryDirectory() as tmpdir:
            machine_dir = os.path.join(tmpdir, 'MACHINE')
            valid_dir = os.path.join(machine_dir, 'PREFERENCES', 'SYSTEMD')
            os.makedirs(valid_dir, exist_ok=True)
            valid_file = os.path.join(valid_dir, 'SYSTEMD.XML')
            with open(valid_file, 'w', encoding='utf-8') as file_obj:
                file_obj.write('<?xml version="1.0" encoding="UTF-8"?><Systemds clsid="{ROOT}"/>')

            invalid_paths = [
                os.path.join(machine_dir, 'PREFERENCES', 'SYSTEMDS', 'SYSTEMDS.XML'),
                os.path.join(machine_dir, 'PREFERENCES', 'SYSTEMDS', 'SYSTEMD.XML'),
                os.path.join(machine_dir, 'PREFERENCES', 'SYSTEMD', 'SYSTEMDS.XML'),
            ]
            for path in invalid_paths:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as file_obj:
                    file_obj.write('<?xml version="1.0" encoding="UTF-8"?><Systemds clsid="{ROOT}"/>')

            found = gpt_helpers.find_preffile(machine_dir, 'systemd')
            self.assertEqual(found, valid_file)
            self.assertEqual(gpt_helpers.get_preftype(valid_file), gpt_helpers.FileType.SYSTEMDS)


if __name__ == '__main__':
    unittest.main()
