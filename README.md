# GPOA - GPO Applier for Linux

## Contents

* [Introduction](#introduction)
* [Packages](#packages)
* [Features](#features)
* [Architecture](#architecture)
* [Installation](#installation)
* [Usage](#usage)
* [External API (gpoa-lib)](#external-api-gpoa-lib)
* [Plugin Development](#plugin-development)
* [Project Structure](#project-structure)
* [Contributing](#contributing)
* [License](#license)

* * *

## Introduction

GPOA (GPO Applier for Linux) is a comprehensive facility to fetch, reinterpret and apply Group Policy Objects (GPOs) from Windows Active Directory domains in Linux environments. Developed by ALT Linux team, it enables seamless integration of Linux machines into corporate Windows infrastructure.


## Packages

Starting from version 0.16.0, the project is split into two RPM packages:

| Package | Description |
|---------|-------------|
| **gpupdate** | Entry points, backends, GPT processing. Depends on `gpoa-lib`. |
| **gpoa-lib** | Standalone library: policy appliers, storage, plugin framework, utilities. Can be used independently. |

The `gpoa/` directory contains thin wrappers that re-export from `gpoa_lib/` for backward compatibility. All implementation lives in `gpoa_lib/`.

## Features

### Core Functionality
- **Multi-backend Support**: Samba, FreeIPA, and no-domain backends
- **Policy Types**: Registry settings, files, folders, environment variables, scripts, services, and more
- **Display Manager Integration**: LightDM, GDM, SDDM with background and theme support
- **Plugin System**: Extensible architecture for custom policy types
- **Targeting Filters**: 15 filter types (computer, domain, user, group, date, time, CPU, battery, disk, RAM, language, file, environment variable, IP range, MAC range)
- **Privilege Separation**: Secure execution with proper privilege contexts
- **External API**: `StorageAdapter` and `ApplierRunner` for using gpoa-lib as a standalone library

### Supported Policy Areas
- **System Configuration**: Control facilities, systemd units, environment variables, NTP, firewall
- **Desktop Settings**: GSettings, KDE configuration
- **Security**: Polkit policies, LAPS (Local Administrator Password Solution)
- **Network**: CIFS/autofs network shares
- **Applications**: Firefox, Chromium, Thunderbird, Yandex Browser
- **Files and Folders**: File deployment, folder redirection, INI file configuration
- **Hardware**: Udev rules (via external plugin)

## Architecture

### Backend System
- **Samba Backend**: Traditional Active Directory integration
- **FreeIPA Backend**: Enhanced FreeIPA/IdM integration
- **No-domain Backend**: Local policy application

### Frontend System
- **Policy Appliers**: 20 specialized modules for different policy types
- **Plugin Framework**: Extensible plugin system with logging and translations
- **Targeting Filters**: GPP preference-level targeting with caching

### Storage
- **Dconf Registry**: Policy data stored in dconf databases
- **GPP State**: Lifecycle management (applyOnce, removePolicy, disabled)
- **File Cache**: Secure file storage and retrieval

### Plugin System
- **Machine Context**: Root-privileged system-wide changes
- **User Context**: User-specific configuration application with privilege dropping
- **Message Codes**: Structured logging with translation support
- **Registry Access**: Secure access to policy registry data via `get_dict_registry()`
- **Custom registry_path**: Override registry path at construction time

## Installation

### From Source
```bash
# Clone the repository
git clone https://github.com/altlinux/gpupdate.git
cd gpupdate

# Build RPM packages (produces gpupdate and gpoa-lib)
rpmbuild -ba gpupdate.spec

# Install both packages
rpm -ivh ~/rpmbuild/RPMS/noarch/gpupdate-*.rpm ~/rpmbuild/RPMS/noarch/gpoa-lib-*.rpm

# Or install only the library
rpm -ivh ~/rpmbuild/RPMS/noarch/gpoa-lib-*.rpm
```

### Dependencies
- Python 3.10+
- Samba client tools
- FreeIPA client (optional)
- Systemd
- D-Bus

## Usage

### Apply Policies for Machine
```bash
# Run as root for system-wide policies
sudo gpoa
```

### Apply Policies for User
```bash
# Run as root for user-specific policies
sudo gpoa username
```

### Force Policy Refresh
```bash
# Can be run as regular user
gpupdate --force
```

### Plugin Management
Plugins are automatically discovered from:
- `/usr/lib/gpoa/plugins/` (system-wide plugins)
- `gpoa_lib/gpoa_lib/frontend_plugins/` (built-in plugins)

## External API (gpoa-lib)

`gpoa-lib` provides a public API for applying policies without the full gpupdate stack.

### ApplierRunner

High-level facade for running policy appliers:

```python
from gpoa_lib import ApplierRunner

# From a dconf database
runner = ApplierRunner(db_name='mydb')
runner.run('control')

# From a plain dict (no dconf needed)
runner = ApplierRunner(data={
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
    }
})
runner.run('control')

# List available appliers
print(ApplierRunner.list_appliers())
```

### StorageAdapter

Low-level access to policy data from dconf or dict:

```python
from gpoa_lib import StorageAdapter

# From dconf database
storage = StorageAdapter.from_dconf_db('mydb')

# From dict
storage = StorageAdapter.from_dict({
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
    }
})

# Get raw dict (for passing to plugins)
data = storage.get_dict()

# Query specific entries
entries = storage.filter_hklm_entries('Software/BaseALT/Policies/Control')
value = storage.get_key_value('Software/BaseALT/Policies/Control/sshd-gssapi-auth')
```

### Running Plugins with Custom Data

```python
import sys
sys.path.insert(0, '/usr/lib/gpoa/plugins')

from gpoa_lib import StorageAdapter
from udev_applier import UdevApplier

# From dict with default registry path
storage = StorageAdapter.from_dict({
    'Software/BaseALT/Policies/Udev': {'BlockUSBAll': '1'}
})
plugin = UdevApplier(storage.get_dict())
plugin.apply()

# With custom registry_path
plugin = UdevApplier(storage.get_dict(), registry_path='My/Custom/Path')
plugin.apply()
```

See [gpoa_lib/EXAMPLES.md](gpoa_lib/EXAMPLES.md) for complete examples.

## Plugin Development

GPOA features a comprehensive plugin system. See documentation for detailed information:

- [PLUGIN_DEVELOPMENT_GUIDE.md](PLUGIN_DEVELOPMENT_GUIDE.md) - English version
- [PLUGIN_DEVELOPMENT_GUIDE_RU.md](PLUGIN_DEVELOPMENT_GUIDE_RU.md) - Russian version

Documentation covers:
- Plugin architecture and API
- Creating custom plugins
- Logging and message codes
- Translation support
- Best practices

### Quick Plugin Example
```python
from gpoa_lib.plugin.plugin_base import FrontendPlugin


class MyPlugin(FrontendPlugin):
    domain = 'my_plugin'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
        super().__init__(dict_dconf_db, username, fs_file_cache, registry_path)
        self._init_plugin_log(message_dict={
            'i': {1: "Plugin initialized"},
            'e': {1: "Plugin failed"}
        }, domain="my_plugin")
        self.config = self.get_dict_registry(
            self._registry_path or 'Software/MyOrg/Policies/MyPlugin')

    def run(self, **kwargs):
        self.log("I1")
        return True


def create_machine_applier(dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
    return MyPlugin(dict_dconf_db, username, fs_file_cache, registry_path)
```

## Project Structure

```
gpupdate/
├── gpoa/                  # Entry points, backends, GPT processing
│   ├── backend/           # Samba, FreeIPA, nodomain backends
│   ├── gpt/               # GPT parsing and filter processing
│   ├── frontend/          # Thin wrappers → gpoa_lib
│   ├── util/              # Thin wrappers → gpoa_lib
│   └── *.py               # Thin wrappers → gpoa_lib
│
├── gpoa_lib/
│   └── gpoa_lib/          # Standalone library (installable as gpoa-lib RPM)
│       ├── frontend/      # 20 policy appliers
│       │   └── appliers/  # Individual applier implementations
│       ├── plugin/        # Plugin framework (base, manager, logging)
│       ├── storage/       # Dconf registry, GPP state, StorageAdapter
│       ├── util/          # Utilities, filters, logging
│       ├── messages/      # Localized message definitions
│       └── test/          # Unit tests
│
├── gpresult/              # Separate package (own pyproject.toml)
├── gpupdate.spec          # RPM spec (gpupdate + gpoa-lib subpackage)
└── AGENTS.md              # Development guide
```

## Contributing

The main communication channel for GPOA is [Samba@ALT Linux mailing lists](https://lists.altlinux.org/mailman/listinfo/samba). The mailing list is in Russian but you may also send e-mail in English or German.


## License

GPOA - GPO Applier for Linux

Copyright (C) 2019-2026 BaseALT Ltd.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
