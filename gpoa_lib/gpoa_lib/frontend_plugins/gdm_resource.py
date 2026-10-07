# Copyright (C) 2026 BaseALT Ltd. <info@basealt.ru>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Checked, atomic updates of the installed GDM theme resource."""

import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from ..util.atomic_files import publish_files


def read_resources(path):
    listing = subprocess.run(['gresource', 'list', str(path)], check=True,
                             capture_output=True, text=True, timeout=30)
    names = listing.stdout.splitlines()
    if not names or len(set(names)) != len(names):
        raise ValueError('Empty or duplicate GResource entries')
    entries = {}
    for name in names:
        if not name.startswith('/') or '\x00' in name:
            raise ValueError('Invalid GResource alias')
        # Resources may contain binary data; never decode their contents here.
        entries[name] = subprocess.run(
            ['gresource', 'extract', str(path), name], check=True,
            capture_output=True, timeout=30).stdout
    return entries


def update_background(entries, background):
    uri = Path(background).as_uri()
    targets = {'gnome-shell.css', 'gnome-shell-dark.css', 'gnome-shell-light.css',
               'gnome-shell-high-contrast.css'}
    updated = dict(entries)
    matches = 0

    def replace_block(match):
        # Preserve unrelated properties, including a fallback background color.
        body = re.sub(r'\bbackground(?:-image|-size|-repeat|-position)?\s*:[^;{}]*(?:;|$)',
                      '', match.group(1)).strip()
        return ('#lockDialogGroup {\n  ' + body + '\n'
                '  background-image: url("' + uri + '");\n'
                '  background-repeat: no-repeat;\n'
                '  background-size: cover;\n'
                '  background-position: center;\n}')

    for name, content in entries.items():
        if name.rsplit('/', 1)[-1] not in targets:
            continue
        text = content.decode('utf-8')
        text, count = re.subn(r'#lockDialogGroup\s*\{([^{}]*)\}', replace_block, text)
        if count:
            updated[name] = text.encode('utf-8')
            matches += count
        elif name.endswith(('gnome-shell-dark.css', 'gnome-shell-light.css')):
            raise ValueError('No supported lockDialogGroup rule in ' + name)
    if not matches:
        raise ValueError('No supported GDM background CSS rules')
    return updated


@contextmanager
def resource_lock(path):
    # A stable lock inode is required because the resource itself is replaced.
    fd = os.open(str(path) + '.gpupdate.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def compile_resources(entries, directory, target):
    root = ET.Element('gresources')
    resource = ET.SubElement(root, 'gresource', prefix='/')
    for index, (alias, data) in enumerate(entries.items()):
        # Physical filenames are independent of aliases (nested names and
        # duplicate basenames are valid; aliases never become filesystem paths).
        filename = 'entry-{}'.format(index)
        (directory / filename).write_bytes(data)
        ET.SubElement(resource, 'file', alias=alias[1:]).text = filename
    manifest = directory / 'theme.gresource.xml'
    ET.ElementTree(root).write(manifest, encoding='utf-8', xml_declaration=True)
    subprocess.run(['glib-compile-resources', '--target', str(target), str(manifest)],
                   cwd=str(directory), check=True, capture_output=True, timeout=60)
    if read_resources(target) != entries:
        raise ValueError('Compiled resource does not match the prepared contents')


def _publish(candidate, target, original, companions=None):
    if target.read_bytes() != original:
        raise RuntimeError('GDM resource changed during preparation')
    contents = dict(companions or {})
    contents[target] = candidate.read_bytes()
    publish_files(contents, expected={target: original})


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _state_path(target):
    return Path(str(target) + '.gpupdate-state.json')


def _read_state(target):
    path = _state_path(target)
    if not path.exists():
        return None
    state = json.loads(path.read_text())
    if (not isinstance(state, dict) or any(not isinstance(state.get(key), str)
            or not re.fullmatch('[0-9a-f]{64}', state[key]) for key in ('baseline', 'published'))):
        raise ValueError('Invalid GDM resource generation metadata')
    return state


def apply_background(resource_path, background):
    target = Path(resource_path).resolve(strict=True)
    with resource_lock(target), tempfile.TemporaryDirectory(prefix='gpoa_gdm_') as temporary:
        original = target.read_bytes()
        entries = read_resources(target)
        updated = update_background(entries, background)
        backup = Path(str(target) + '.backup')
        previous_backup = backup.read_bytes() if backup.exists() else None
        state = _read_state(target)
        same_generation = (state is not None and previous_backup is not None
                           and _digest(previous_backup) == state['baseline']
                           and _digest(original) in (state['baseline'], state['published']))
        if updated == entries and same_generation:
            return
        # An external replacement (for example an RPM upgrade) establishes a
        # new baseline. Never use an unverified legacy backup to downgrade it.
        baseline = previous_backup if same_generation else original
        # The candidate and backup staging files share the destination filesystem.
        with tempfile.TemporaryDirectory(prefix='.gpupdate-', dir=target.parent) as staging:
            candidate = Path(staging) / 'theme.gresource'
            compile_resources(updated, Path(temporary), candidate)
            if target.read_bytes() != original:
                raise RuntimeError('GDM resource changed during preparation')
            published = candidate.read_bytes()
            state = {'baseline': _digest(baseline), 'published': _digest(published)}
            companions = {backup: baseline,
                          _state_path(target): json.dumps(state).encode('utf-8')}
            if previous_backup is not None and previous_backup != baseline:
                history = Path(str(backup) + '.' + _digest(previous_backup))
                if not history.exists():
                    companions[history] = previous_backup
            _publish(candidate, target, original, companions)


def restore_background(resource_path):
    target = Path(resource_path).resolve(strict=True)
    with resource_lock(target):
        backup = Path(str(target) + '.backup')
        original = target.read_bytes()
        read_resources(backup)  # Refuse to publish an invalid/incomplete backup.
        baseline = backup.read_bytes()
        if original == baseline:
            return
        state = _read_state(target)
        if (state is None or state['baseline'] != _digest(baseline)
                or state['published'] != _digest(original)):
            raise ValueError('GDM backup does not belong to the installed resource generation')
        with tempfile.TemporaryDirectory(prefix='.gpupdate-', dir=target.parent) as staging:
            candidate = Path(staging) / 'theme.gresource'
            shutil.copyfile(backup, candidate)
            state['published'] = state['baseline']
            _publish(candidate, target, original,
                     {_state_path(target): json.dumps(state).encode('utf-8')})
