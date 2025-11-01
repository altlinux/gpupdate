# GPOA - GPO Applier for Linux

## Contents

* [Introduction](#introduction)
* [Features](#features)
* [Architecture](#architecture)
* [Installation](#installation)
* [Usage](#usage)
* [Plugin Development](#plugin-development)
* [Contributing](#contributing)
* [License](#license)

* * *

## Introduction

GPOA (GPO Applier for Linux) is a comprehensive facility to fetch, reinterpret and apply Group Policy Objects (GPOs) from Windows Active Directory domains in Linux environments. Developed by ALT Linux team, it enables seamless integration of Linux machines into corporate Windows infrastructure.


## Features

### Core Functionality
- **Multi-backend Support**: Samba, FreeIPA, and no-domain backends
- **Policy Types**: Registry settings, files, folders, environment variables, scripts, services, and more
- **Display Manager Integration**: LightDM, GDM with background and theme support
- **Plugin System**: Extensible architecture for custom policy types
- **Privilege Separation**: Secure execution with proper privilege contexts

### Supported Policy Areas
- **System Configuration**: Environment variables, services
- **Desktop Settings**: GSettings, KDE configuration, browser policies
- **Security**: Polkit policies
- **Network**: Network shares
- **Applications**: Firefox, Chrome, Thunderbird, Yandex Browser
- **Files and Folders**: File deployment, folder redirection

## Architecture

### Backend System
- **Samba Backend**: Traditional Active Directory integration
- **FreeIPA Backend**: Enhanced FreeIPA/IdM integration
- **No-domain Backend**: Local policy application

### Frontend System
- **Policy Appliers**: Specialized modules for different policy types
- **Plugin Framework**: Extensible plugin system with logging and translations

### Plugin System
- **Machine Context**: Root-privileged system-wide changes
- **User Context**: User-specific configuration application
- **Message Codes**: Structured logging with translation support
- **Registry Access**: Secure access to policy registry data

## Installation

### From Source
```bash
# Clone the repository
git clone https://github.com/altlinux/gpupdate.git
cd gpupdate

# Build RPM package
rpmbuild -ba gpupdate.spec

# Install the package
rpm -ivh ~/rpmbuild/RPMS/noarch/gpupdate-*.rpm
```

### Dependencies
- Python 3.6+
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
- `/usr/lib/gpupdate/plugins/` (system plugins)
- `gpoa/frontend_plugins/` (development plugins)

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
from gpoa.plugin.plugin_base import FrontendPlugin

class MyPlugin(FrontendPlugin):
    domain = 'my_plugin'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None):
        super().__init__(dict_dconf_db, username, fs_file_cache)
        self._init_plugin_log(message_dict={
            'i': {1: "Plugin initialized"},
            'e': {1: "Plugin failed"}
        }, domain="my_plugin")

    def run(self):
        self.log("I1")
        return True

def create_machine_applier(dict_dconf_db, username=None, fs_file_cache=None):
    return MyPlugin(dict_dconf_db, username, fs_file_cache)
```


## Contributing

The main communication channel for GPOA is [Samba@ALT Linux mailing lists](https://lists.altlinux.org/mailman/listinfo/samba). The mailing list is in Russian but you may also send e-mail in English or German.


## License

GPOA - GPO Applier for Linux

Copyright (C) 2019-2025 BaseALT Ltd.

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

