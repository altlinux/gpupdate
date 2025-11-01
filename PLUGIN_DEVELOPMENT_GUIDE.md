# GPOA Plugin Development Guide

## Introduction

GPOA (GPO Applier for Linux) supports a plugin system for extending group policy application functionality.
Plugins allow adding support for new policy types and system settings without modifying the core code.

## Plugin Architecture

### Base Classes

- **`plugin`** - Abstract base class with final methods `apply()` and `apply_user()`
- **`FrontendPlugin`** - Simplified class for plugins with logging support

### Plugin Manager

- **`plugin_manager`** - Loads and executes plugins from directories:
  - `/usr/lib/gpupdate/plugins/` - system plugins
  - `gpoa/frontend_plugins/` - development plugins

## Creating a Simple Plugin

### Example: Basic Plugin with Logging

```python
#!/usr/bin/env python3
#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2025 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from gpoa.plugin.plugin_base import FrontendPlugin


class ExampleApplier(FrontendPlugin):
    """
    Example simple plugin with logging and registry access.
    """

    # Domain for translations
    domain = 'example_applier'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None):
        """
        Initialize the plugin.

        Args:
            dict_dconf_db (dict): Dictionary with registry data
            username (str): Username
            fs_file_cache: File system cache
        """
        super().__init__(dict_dconf_db, username, fs_file_cache)

        # Initialize logging system
        self._init_plugin_log(
            message_dict={
                'i': {  # Informational messages
                    1: "Example Applier initialized",
                    2: "Configuration applied successfully"
                },
                'w': {  # Warnings
                    10: "No configuration found in registry"
                },
                'e': {  # Errors
                    20: "Failed to apply configuration"
                }
            },
            domain="example_applier"
        )

    def run(self):
        """
        Main plugin execution method.

        Returns:
            bool: True if successful, False on error
        """
        try:
            self.log("I1")  # Plugin initialized

            # Get data from registry
            self.config = self.get_dict_registry('Software/BaseALT/Policies/Example')

            if not self.config:
                self.log("W10")  # No configuration found in registry
                return True

            # Log registry data
            self.log("I2")  # Configuration applied successfully

            return True

        except Exception as e:
            self.log("E20", {"error": str(e)})
            return False


def create_machine_applier(dict_dconf_db, username=None, fs_file_cache=None):
    """
    Factory function for creating plugin instance for machine context.

    Args:
        dict_dconf_db (dict): Dictionary with registry data
        username (str): Username
        fs_file_cache: File system cache

    Returns:
        ExampleApplier: Plugin instance
    """
    return ExampleApplier(dict_dconf_db, username, fs_file_cache)


def create_user_applier(dict_dconf_db, username=None, fs_file_cache=None):
    """
    Factory function for creating plugin instance for user context.

    Args:
        dict_dconf_db (dict): Dictionary with registry data
        username (str): Username
        fs_file_cache: File system cache

    Returns:
        ExampleApplier: Plugin instance
    """
    return ExampleApplier(dict_dconf_db, username, fs_file_cache)
```

## Key Plugin Elements

### 1. Log Registration

Plugins use a logging system with message codes:

```python
self._init_plugin_log(
    message_dict={
        'i': {  # Informational messages
            1: "Example Applier initialized",
            2: "Configuration applied successfully"
        },
        'w': {  # Warnings
            10: "No configuration found in registry"
        },
        'e': {  # Errors
            20: "Failed to apply configuration"
        }
    },
    domain="example_applier"
)
```

### 2. Registry Access

Access registry data through `get_dict_registry()` method:

```python
self.config = self.get_dict_registry('Software/BaseALT/Policies/Example')
```

### 3. Logging in run Method

Using registered message codes:

```python
self.log("I1")  # Simple message
self.log("E20", {"error": str(e)})  # Message with data
```

### 4. Factory Functions

Plugins must provide factory functions:

- `create_machine_applier()` - for machine context
- `create_user_applier()` - for user context

## Translation System

### Localization Support

GPOA supports automatic localization of plugin messages. The system uses standard GNU gettext.

### Translation File Structure

```
gpoa/locale/
├── ru/
│   └── LC_MESSAGES/
│       ├── gpoa.mo
│       └── gpoa.po
└── en/
    └── LC_MESSAGES/
        ├── gpoa.mo
        └── gpoa.po
```

### Setting Up Translations in Plugin

1. **Define translation domain**:
```python
class MyPlugin(FrontendPlugin):
    domain = 'my_plugin'  # Domain for translation files
```

2. **Initialize logger with translation support**:
```python
self._init_plugin_log(
    message_dict={
        'i': {
            1: "Plugin initialized",
            2: "Configuration applied successfully"
        },
        'e': {
            10: "Configuration error"
        }
    },
    domain="my_plugin"  # Domain for translation file lookup
)
```

3. **Usage in code**:
```python
# Messages are automatically translated when logged
self.log("I1")  # Will be displayed in system language
```

### Creating Translation Files

1. **Extract strings for translation**:
```bash
# Extract strings from plugin code
xgettext -d my_plugin -o my_plugin.po my_plugin.py
```

2. **Create translation file**:
```po
# my_plugin.po
msgid "Plugin initialized"
msgstr ""

msgid "Configuration applied successfully"
msgstr ""
```

3. **Compile translations**:
```bash
# Compile .po to .mo
msgfmt my_plugin.po -o my_plugin.mo

# Place in correct directory
mkdir -p /usr/share/locale/ru/LC_MESSAGES/
cp my_plugin.mo /usr/share/locale/ru/LC_MESSAGES/
```

### Best Practices for Translations

1. **Use complete sentences** - don't split strings into parts
2. **Avoid string concatenation** - this complicates translation
3. **Provide context** - add comments for translators
4. **Test translations** - verify display in different languages
5. **Update translations** - update .po files when messages change

### Example Plugin Structure with Translations

```
my_plugin/
├── my_plugin.py          # Main plugin code
├── locale/
│   ├── ru/
│   │   └── LC_MESSAGES/
│   │       ├── my_plugin.mo
│   │       └── my_plugin.po
│   └── en/
│       └── LC_MESSAGES/
│           ├── my_plugin.mo
│           └── my_plugin.po
└── README.md
```

## Plugin API

### Core Methods

- **`__init__(dict_dconf_db, username=None, fs_file_cache=None)`** - initialization
- **`run()`** - main execution method (abstract)
- **`apply()`** - execute with current privileges (final)
- **`apply_user(username)`** - execute with user privileges (final)
- **`get_dict_registry(prefix='')`** - get registry data
- **`_init_plugin_log(message_dict=None, locale_dir=None, domain=None)`** - initialize logger
- **`log(message_code, data=None)`** - logging with message codes

### Logging System

Message codes:
- **I** - Informational messages
- **W** - Warnings
- **E** - Errors
- **D** - Debug messages
- **F** - Fatal errors

### Data Access

- **`dict_dconf_db`** - dictionary with registry data
- **`username`** - username (for user context)
- **`fs_file_cache`** - file system cache for file operations

## Execution Contexts

### Machine Context

- Executed with root privileges
- Applies system-wide settings
- Uses factory function `create_machine_applier()`

### User Context

- Executed with specified user privileges
- Applies user-specific settings
- Uses factory function `create_user_applier()`

## Best Practices

1. **Security**: Always validate input data
2. **Idempotence**: Repeated execution should produce the same result
3. **Logging**: Use message codes for all operations
4. **Error Handling**: Plugin should not crash on errors
5. **Transactional**: Changes should be atomic
6. **Translations**: Support message localization
