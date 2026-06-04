# gpoa_lib External API Examples

## Control Applier Examples

### Method 1: ApplierRunner from dconf database
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(db_name='mydb')
result = runner.create('control')
if result:
    result.data.apply()
```

### Method 2: ApplierRunner from dconf database + custom prefix
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(db_name='mydb')
# Looks under: Software/MyOrg/Policies/Control (applier name appended)
runner.run('control', prefix='Software/MyOrg/Policies')
```

### Method 3: ApplierRunner from dconf database + specific keys
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(db_name='mydb')
runner.run('control', keys=[
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
    'Software/BaseALT/Policies/Control/writeable',
])
```

### Method 4: ApplierRunner from dict (no dconf needed)
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(data={
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
        'writeable': '0',
    }
})
runner.run('control')
```

### Method 5: Direct via StorageAdapter + applier class
```python
from gpoa_lib import StorageAdapter
from gpoa_lib.frontend import control_applier

storage = StorageAdapter.from_dict({
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
    }
})
ctrl = control_applier(storage)
ctrl.apply()
```

### Method 6: StorageAdapter from dconf database
```python
from gpoa_lib import StorageAdapter
from gpoa_lib.frontend import control_applier

storage = StorageAdapter.from_dconf_db('mydb')
ctrl = control_applier(storage)
ctrl.apply()
```

### Method 7: StorageAdapter from dconf + custom prefix
```python
from gpoa_lib import StorageAdapter
from gpoa_lib.frontend import control_applier

storage = StorageAdapter.from_dconf_db_prefix(
    'mydb',
    prefix='Software/MyOrg/Policies/Control',
)
ctrl = control_applier(storage)
ctrl.apply()
```

## List Available Appliers

```python
from gpoa_lib import ApplierRunner

print(ApplierRunner.list_appliers())
# ['control', 'chromium', 'firefox', 'thunderbird', 'yandex_browser',
#  'firewall', 'gsettings', 'kde', 'ntp', 'package', 'polkit', 'systemd']
```

## Plugin Examples

### Minimal plugin (machine-only)

Create a file `/usr/lib/gpoa/plugins/my_plugin.py`:

```python
from gpoa_lib.plugin.plugin_base import FrontendPlugin


class MyPlugin(FrontendPlugin):
    plugin_name = 'my_plugin'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
        super().__init__(dict_dconf_db, username, fs_file_cache, registry_path)
        self._init_plugin_log(
            message_dict={
                'i': {1: "MyPlugin started"},
                'w': {1: "No configuration found"},
            },
            domain="my_plugin",
        )
        self.config = self.get_dict_registry('Software/MyOrg/Policies/MyPlugin')

    def run(self, **kwargs):
        self.log("I1")
        if not self.config:
            self.log("W1")
            return
        # Apply configuration...
        for key, value in self.config.items():
            pass  # your logic here


def create_machine_applier(dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
    return MyPlugin(dict_dconf_db, username, fs_file_cache, registry_path)
```

### Plugin with machine + user contexts

```python
from gpoa_lib.plugin.plugin_base import FrontendPlugin


class DualPlugin(FrontendPlugin):
    plugin_name = 'dual_plugin'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
        super().__init__(dict_dconf_db, username, fs_file_cache, registry_path)
        self._init_plugin_log(
            message_dict={
                'i': {1: "DualPlugin running for {who}"},
            },
            domain="dual_plugin",
        )
        self.config = self.get_dict_registry('Software/MyOrg/Policies/Dual')

    def run(self, **kwargs):
        who = self.username or 'machine'
        self.log("I1", {"who": who})


def create_machine_applier(dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
    return DualPlugin(dict_dconf_db, username, fs_file_cache, registry_path)


def create_user_applier(dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
    return DualPlugin(dict_dconf_db, username, fs_file_cache, registry_path)
```

### Run plugins programmatically via plugin_manager

```python
from gpoa_lib.plugin.plugin_manager import plugin_manager

# Machine context
pm = plugin_manager(is_machine=True, username=None)
pm.run()

# User context
pm = plugin_manager(is_machine=False, username='someuser')
pm.run()

# Get a specific loaded plugin by name
plugin = pm.get_plugin('my_plugin')
if plugin:
plugin.apply()
```

## StorageWriter Examples

### Write to local database
```python
from gpoa_lib import StorageWriter

writer = StorageWriter('local')
writer.write_keys({
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth': '1',
    'Software/BaseALT/Policies/Control/ssh-gssapi-auth': 'enabled',
})
writer.compile()
```

### Write nested dict and compile
```python
from gpoa_lib import StorageWriter

writer = StorageWriter('mydb')
writer.write({
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
    }
})
writer.compile()
```

### Delete keys from database
```python
from gpoa_lib import StorageWriter

writer = StorageWriter('local')
writer.delete_keys([
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
])
writer.compile()
```

## Result Examples

### Handle run result
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(data={
    'Software/BaseALT/Policies/Control': {'sshd-gssapi-auth': '1'},
})
result = runner.run('control')
if result:
    print('Applied successfully')
else:
    print('Error:', result.error)
```

### Check create result
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(data={})
result = runner.create('control')
if result:
    applier = result.data
    applier.apply()
else:
    print(f'Could not create: {result.error}')
```

## Auto-resolve Examples

### Resolve applier name from key path
```python
from gpoa_lib import ApplierRunner

name = ApplierRunner.resolve('Software/BaseALT/Policies/Control/sshd-gssapi-auth')
print(name)  # 'control'

name = ApplierRunner.resolve('Software/Policies/Mozilla/Firefox')
print(name)  # 'firefox'
```

### Run with auto-detection
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(data={
    'Software/BaseALT/Policies/Control': {'sshd-gssapi-auth': '1'},
})
name = runner.run_auto([
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
])
print(name)  # 'control'
```

## Force Application Examples

### Force re-apply from specific database
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(db_name='policy', force=True)
result = runner.run('control')
```

### Force from dict with auto-resolve
```python
from gpoa_lib import ApplierRunner

runner = ApplierRunner(data={
    'Software/BaseALT/Policies/KDE': {'kwinrc': '1'},
}, force=True)
result = runner.run('kde')
```

### Standalone plugin without plugin_manager

```python
from gpoa_lib import StorageAdapter
from gpoa_lib.plugin.plugin_base import FrontendPlugin

# Define a custom plugin inline
class HelloPlugin(FrontendPlugin):
    plugin_name = 'hello'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
        super().__init__(dict_dconf_db, username, fs_file_cache, registry_path)

    def run(self, **kwargs):
        greeting = self.get_dict_registry('Software/MyOrg/Hello')
        msg = greeting.get('Message', 'Hello World')
        print(msg)

# Use with StorageAdapter
storage = StorageAdapter.from_dict({
    'Software/MyOrg/Hello': {
        'Message': 'Hello from gpoa_lib!',
    }
})
plugin = HelloPlugin(storage.get_dict())
plugin.apply()
# Output: Hello from gpoa_lib!
```

### Plugin with locale/translations

Create a file `/usr/lib/gpoa/plugins/localized_plugin.py` and a
`locale/` directory next to it with standard gettext layout
(`ru/LC_MESSAGES/localized_plugin.po` / `.mo`):

```python
from gpoa_lib.plugin.plugin_base import FrontendPlugin


class LocalizedPlugin(FrontendPlugin):
    plugin_name = 'localized_plugin'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
        super().__init__(dict_dconf_db, username, fs_file_cache, registry_path)
        self._init_plugin_log(
            message_dict={
                'i': {1: "Localized greeting: {text}"},
                'w': {1: "Missing key {key}"},
            },
            domain="localized_plugin",
        )
        self.config = self.get_dict_registry('Software/MyOrg/Localized')

    def run(self, **kwargs):
        text = self.config.get('Greeting', '')
        if text:
            self.log("I1", {"text": text})
        else:
            self.log("W1", {"key": "Greeting"})


def create_machine_applier(dict_dconf_db, username=None, fs_file_cache=None, registry_path=None):
    return LocalizedPlugin(dict_dconf_db, username, fs_file_cache, registry_path)
```

## Run Existing Plugin with Custom Data

Use `StorageAdapter.get_dict()` to feed arbitrary data into any existing plugin.

> **Note:** External plugins are installed in `/usr/lib/gpoa/plugins/` which
> is not on Python's `sys.path`. You need to add it before importing:
> ```python
> import sys
> sys.path.insert(0, '/usr/lib/gpoa/plugins')
> ```

### From a specific dconf database

```python
import sys
sys.path.insert(0, '/usr/lib/gpoa/plugins')

from gpoa_lib import StorageAdapter
from udev_applier import UdevApplier

storage = StorageAdapter.from_dconf_db('my_custom_db')
plugin = UdevApplier(storage.get_dict())
plugin.apply()
```

### From a dconf database with prefix filter

```python
import sys
sys.path.insert(0, '/usr/lib/gpoa/plugins')

from gpoa_lib import StorageAdapter
from udev_applier import UdevApplier

storage = StorageAdapter.from_dconf_db_prefix(
    'my_custom_db',
    prefix='Software/BaseALT/Policies/Udev',
)
plugin = UdevApplier(storage.get_dict())
plugin.apply()
```

### From specific keys in a dconf database

```python
import sys
sys.path.insert(0, '/usr/lib/gpoa/plugins')

from gpoa_lib import StorageAdapter
from udev_applier import UdevApplier

storage = StorageAdapter.from_dconf_db_keys('my_custom_db', [
    'Software/BaseALT/Policies/Udev/BlockUSBAll',
    'Software/BaseALT/Policies/Udev/USBAllowList',
])
plugin = UdevApplier(storage.get_dict())
plugin.apply()
```

### From plain dict (no dconf needed)

```python
import sys
sys.path.insert(0, '/usr/lib/gpoa/plugins')

from gpoa_lib import StorageAdapter
from udev_applier import UdevApplier

storage = StorageAdapter.from_dict({
    'Software/BaseALT/Policies/Udev': {
        'BlockUSBAll': '1',
        'USBAllowList': '1234:5678;abcd:ef01',
    }
})
plugin = UdevApplier(storage.get_dict())
plugin.apply()
```

### Override registry_path

Pass `registry_path` to use a different registry key than the plugin's default:

```python
import sys
sys.path.insert(0, '/usr/lib/gpoa/plugins')

from gpoa_lib import StorageAdapter
from udev_applier import UdevApplier

storage = StorageAdapter.from_dict({
    'MyOrg/Custom/Udev': {
        'BlockUSBAll': '1',
    }
})
plugin = UdevApplier(storage.get_dict(), registry_path='MyOrg/Custom/Udev')
plugin.apply()
```

### From dconf database with custom registry_path

```python
import sys
sys.path.insert(0, '/usr/lib/gpoa/plugins')

from gpoa_lib import StorageAdapter
from udev_applier import UdevApplier

storage = StorageAdapter.from_dconf_db('mydb')
plugin = UdevApplier(
    storage.get_dict(),
    registry_path='Software/MyOrg/Policies/DeviceRules',
)
plugin.apply()
```
