# gpoa_lib API Reference

This document describes every public class and function exported by the
`gpoa_lib` package.  For a higher-level overview see `README.md`; for plugin
development instructions see `PLUGIN_DEVELOPMENT_GUIDE.md`.

---

## Table of Contents

1. [Result](#result)
2. [StorageAdapter](#storageadapter)
3. [StorageWriter](#storagewriter)
4. [ApplierRunner](#applierrunner)
5. [plugin (abstract base)](#plugin)
6. [FrontendPlugin](#frontendplugin)
7. [applier_frontend](#applier_frontend)
8. [DualContextApplier](#dualcontextapplier)
9. [plugin_manager](#plugin_manager)
10. [Dconf_registry](#dconf_registry)
11. [GppStateManager](#gppstatemanager)
12. [DynamicAttributes / RegistryKeyMetadata](#dynamicattributes--registrykeymetadata)
13. [Data Types](#data-types)
14. [Filters (FilterChecker)](#filters)
15. [Utility Functions](#utility-functions)
16. [Path Functions](#path-functions)

---

## Quick Import

```python
from gpoa_lib import (
    Result,
    StorageAdapter,
    StorageWriter,
    ApplierRunner,
    FrontendPlugin,
    applier_frontend,
    DualContextApplier,
    Dconf_registry,
    GppStateManager,
    DynamicAttributes,
    RegistryKeyMetadata,
)
```

---

## Result

`gpoa_lib.result.Result`

Type-safe return wrapper for gpoa_lib operations.  Follows the same pattern as
`Result` in Rust/Go: successful operations carry `data`, failed ones carry
`error`.

### Constructor

```python
Result(ok, data=None, error=None)
```

| Parameter | Type   | Description |
|----------|--------|-------------|
| `ok`     | `bool` | Whether the operation succeeded. |
| `data`   | any    | Payload on success. |
| `error`  | `str`  | Error description on failure. |

### Class Methods

#### `Result.ok_result(data=None)`

Create a successful result.

**Returns:** `Result`

#### `Result.fail(error)`

Create a failed result.

| Parameter | Type         | Description |
|----------|--------------|-------------|
| `error`  | `str` or `Exception` | Error description. |

**Returns:** `Result`

### Attributes

| Attribute | Type  | Description |
|-----------|-------|-------------|
| `ok`      | `bool` | `True` on success, `False` on failure. |
| `data`    | any    | Payload (only meaningful when `ok=True`). |
| `error`   | `str`  | Error string (only meaningful when `ok=False`). |

### Usage

```python
result = runner.run('control')
if result:
    print('Applied:', result.data)
else:
    print('Error:', result.error)
```

---

## StorageAdapter

`gpoa_lib.storage.storage_adapter.StorageAdapter`

A lightweight, self-contained policy data reader.  It loads registry data from
a dconf binary database or a plain Python dict and exposes the same query
interface that built-in appliers expect (`filter_hklm_entries`, `get_entry`,
etc.).  Unlike `Dconf_registry`, it carries no global state.

### Constructor

```python
StorageAdapter(db_name=None, uid=None, prefix=None, keys=None, data=None)
```

| Parameter  | Type        | Description |
|-----------|-------------|-------------|
| `db_name`  | `str` or `None` | Database filename under `/etc/dconf/db/`. |
| `uid`      | `int` or `None` | User UID; resolves user-specific dconf path when given. |
| `prefix`   | `str` or `None` | Registry path prefix; only keys under this prefix are kept. |
| `keys`     | `list[str]` or `None` | Exact registry key paths to extract. |
| `data`     | `dict` or `None`  | Plain dict to use directly (no dconf access). |

Only **one** of `db_name` or `data` should be supplied.  At most one of
`prefix` or `keys` may be given.

### Factory Methods

#### `StorageAdapter.from_dict(data)`

Create an adapter from a plain Python dict.

```python
adapter = StorageAdapter.from_dict({
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
    }
})
```

| Parameter | Type  | Description |
|-----------|-------|-------------|
| `data`    | `dict` | Nested dict mapping registry paths to `{name: value}` dicts. |

**Returns:** `StorageAdapter`

---

#### `StorageAdapter.from_dconf_db(db_name, uid=None)`

Load policy data from a dconf binary database.

```python
adapter = StorageAdapter.from_dconf_db('policy')
adapter = StorageAdapter.from_dconf_db('policy', uid=1000)
```

| Parameter  | Type        | Description |
|-----------|-------------|-------------|
| `db_name` | `str`       | Database filename under `/etc/dconf/db/`. |
| `uid`     | `int`       | Optional user UID. Reads `/etc/dconf/db/policy{uid}`. |

**Returns:** `StorageAdapter`

**Requires:** GVdb and GLib GObject introspection packages.

**Path resolution:**
- `from_dconf_db('policy')` → `/etc/dconf/db/policy`
- `from_dconf_db('policy', uid=1000)` → `/etc/dconf/db/policy1000`
- `from_dconf_db('local')` → `/etc/dconf/db/local`

---

#### `StorageAdapter.from_dconf_db_prefix(db_name, prefix, uid=None)`

Load from a dconf database and keep only keys under the given prefix.

```python
adapter = StorageAdapter.from_dconf_db_prefix('policy',
    'Software/BaseALT/Policies/Control')
```

| Parameter | Type        | Description |
|----------|-------------|-------------|
| `db_name` | `str`      | Database filename under `/etc/dconf/db/`. |
| `prefix`  | `str`      | Registry path prefix to filter by. |
| `uid`     | `int`      | Optional user UID. |

**Returns:** `StorageAdapter`

---

#### `StorageAdapter.from_dconf_db_keys(db_name, keys, uid=None)`

Load from a dconf database and keep only the listed keys.

```python
adapter = StorageAdapter.from_dconf_db_keys('policy', [
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
    'Software/BaseALT/Policies/Control/ldap-tls-check',
])
```

| Parameter | Type        | Description |
|----------|-------------|-------------|
| `db_name` | `str`      | Database filename under `/etc/dconf/db/`. |
| `keys`    | `list[str]` | Exact registry key paths to extract. |
| `uid`     | `int`      | Optional user UID. |

**Returns:** `StorageAdapter`

---

### Query Methods

#### `filter_hklm_entries(startswith)`

Return a list of `PregDconf` objects whose keyname starts with `startswith`.
A trailing `%` in `startswith` is stripped before matching.

```python
for entry in adapter.filter_hklm_entries('Software/BaseALT/Policies/Control'):
    print(entry.keyname, entry.valuename, entry.data)
```

| Parameter    | Type   | Description |
|-------------|--------|-------------|
| `startswith` | `str` | Registry path prefix. Trailing `%` is accepted and stripped. |

**Returns:** `list[PregDconf]`

---

#### `filter_hkcu_entries(startswith)`

Alias for `filter_hklm_entries`.  The adapter does not distinguish HKLM / HKCU
hives.

**Returns:** `list[PregDconf]`

---

#### `filter_entries(startswith)`

Alias for `filter_hklm_entries`.

**Returns:** `list[PregDconf]`

---

#### `get_hklm_entry(hive_key)`

Get a single entry as a `PregDconf` object.

| Parameter  | Type  | Description |
|-----------|-------|-------------|
| `hive_key` | `str` | Full registry path, e.g. `Software/BaseALT/Policies/Control/sshd-gssapi-auth`. |

**Returns:** `PregDconf` or `None`

---

#### `get_hkcu_entry(hive_key)`

Alias for `get_hklm_entry`.

**Returns:** `PregDconf` or `None`

---

#### `get_entry(path, preg=True)`

Get a single entry or raw value.

| Parameter | Type   | Description |
|----------|--------|-------------|
| `path`   | `str`  | Full registry path. Backslashes are normalised. |
| `preg`   | `bool` | If `True` (default), return a `PregDconf`. If `False`, return the raw value. |

**Returns:** `PregDconf` | any | `None`

---

#### `get_key_value(key)`

Shorthand for `get_entry(key, preg=False)`.

**Returns:** raw value or `None`

---

#### `get_dict()`

Return a **deep copy** of the internal data dict.  Safe to pass to plugins or
modify without affecting the adapter.

```python
data = adapter.get_dict()
# data is a standalone copy
```

**Returns:** `dict`

---

#### `check_enable_key(key)`

Check whether a registry key is "truthy".  Recognises string values
`True`, `true`, `TRUE`, `yes`, `Yes`, `enabled`, `enable`, `Enabled`,
`Enable`, `1` and non-zero integers.

**Returns:** `bool`

---

## StorageWriter

`gpoa_lib.storage.storage_writer.StorageWriter`

Write policy data to an arbitrary dconf database and compile it.

### Constructor

```python
StorageWriter(db_name, uid=None)
```

| Parameter | Type   | Description |
|----------|--------|-------------|
| `db_name` | `str`  | Database name under `/etc/dconf/db/`. For example `'local'` writes to `/etc/dconf/db/local.d/local.ini`. |
| `uid`     | `int`  | Optional user UID for per-user databases. |

Each `write()` or `write_keys()` call **merges** new data with the existing INI
file. Duplicate sections are never created. Use `clear()` to start fresh.

### Methods

#### `write(data)`

Write a nested dict `{section: {key: value}}` to the database INI file and
create lock entries.

```python
writer = StorageWriter('local')
writer.write({
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
    }
})
writer.compile()
```

| Parameter | Type  | Description |
|----------|-------|-------------|
| `data`   | `dict` | Nested dict of sections and key-value pairs. |

---

#### `write_keys(keys_dict)`

Write a flat dict `{full_path: value}`.  Paths are split at the last `/` into
section and value name.

```python
writer = StorageWriter('local')
writer.write_keys({
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth': '1',
    'Software/BaseALT/Policies/Control/ssh-gssapi-auth': 'enabled',
})
writer.compile()
```

| Parameter   | Type  | Description |
|------------|-------|-------------|
| `keys_dict` | `dict` | Flat dict mapping full registry paths to values. |

---

#### `delete_keys(keys)`

Remove specific keys from the database INI file.  Rewrites the file excluding
the listed keys.

| Parameter | Type        | Description |
|----------|-------------|-------------|
| `keys`   | `list[str]` | Full registry paths to remove. |

---

#### `clear()`

Remove the INI file for this database. The compiled binary database is not
affected; call `compile()` after clearing to regenerate it.

Returns `self` for method chaining.

```python
writer.clear().write({'Section': {'key': 'val'}}).compile()
```

---

#### `compile()`

Compile the database from its INI sources by running `dconf compile`.

---

## ApplierRunner

`gpoa_lib.applier_runner.ApplierRunner`

High-level facade for creating and running built-in appliers.  Handles
`StorageAdapter` construction, extra argument injection (username,
file_cache), and error logging.

### Constructor

```python
ApplierRunner(db_name=None, uid=None, data=None, force=False)
```

| Parameter | Type         | Description |
|----------|-------------|-------------|
| `db_name` | `str` or `None` | Dconf database name (passed to `StorageAdapter`). |
| `uid`     | `int` or `None` | User UID. |
| `data`    | `dict` or `None` | Plain dict; when given, no dconf access is performed. |
| `force`   | `bool` | If `True`, read from the specified database only (bypass merged profile) and re-apply even if target state is already reached. Default `False`. |

### Methods

#### `create(applier_name, prefix=None, keys=None)`

Create an applier instance without running it.

```python
runner = ApplierRunner(data=my_dict)
result = runner.create('control')
if result:
    applier = result.data
    applier.apply()
```

| Parameter       | Type        | Description |
|----------------|-------------|-------------|
| `applier_name` | `str`       | Key in the internal applier map (see table below). |
| `prefix`       | `str`       | Override base prefix. Applier name is appended: `prefix + '/' + applier_name`. |
| `keys`         | `list[str]` | Specific registry keys to load. |

**Returns:** `Result` -- `result.data` holds the applier instance on success.

---

#### `run(applier_name, prefix=None, keys=None)`

Create an applier and call its `apply()` method.  Exceptions are caught and
returned as a failed `Result`.

```python
runner = ApplierRunner(data=my_dict)
result = runner.run('control')
if not result:
    print('Error:', result.error)

runner.run('gsettings', prefix='Software/MyOrg')
```

**Returns:** `Result`

---

#### `resolve(key_or_prefix)`

Determine the applier name from a registry key path or prefix.  Comparison is
case-insensitive and normalises backslashes.

```python
>>> ApplierRunner.resolve('Software/BaseALT/Policies/Control/sshd-gssapi-auth')
'control'
>>> ApplierRunner.resolve('Software/Policies/Mozilla/Firefox')
'firefox'
>>> ApplierRunner.resolve('Software/Unknown/Path')
None
```

| Parameter       | Type  | Description |
|----------------|-------|-------------|
| `key_or_prefix` | `str` | Full registry path or prefix. |

**Returns:** `str` or `None`

---

#### `run_auto(keys)`

Automatically detect the applier from the first key path and run it.

```python
runner = ApplierRunner(data=my_dict)
name = runner.run_auto([
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
])
print(name)  # 'control'
```

| Parameter | Type        | Description |
|----------|-------------|-------------|
| `keys`   | `list[str]` | Registry key paths to apply. |

**Returns:** `str` or `None` -- name of the applier that was run.

---

#### `list_appliers() -> list[str]`

Return the list of available applier names.

```python
>>> ApplierRunner.list_appliers()
['control', 'chromium', 'firefox', 'thunderbird', 'yandex_browser',
 'firewall', 'gsettings', 'kde', 'ntp', 'package', 'polkit', 'systemd']
```

### Applier Map

| Name             | Class                 | Registry Branch                                            | Extra Args         |
|-----------------|-----------------------|-----------------------------------------------------------|--------------------|
| `control`        | `control_applier`     | `Software/BaseALT/Policies/Control`                       | -                  |
| `chromium`       | `chromium_applier`    | `Software/Policies/Google/Chrome`                         | `username`         |
| `firefox`        | `firefox_applier`     | `Software/Policies/Mozilla/Firefox`                       | `username`         |
| `thunderbird`    | `thunderbird_applier` | `Software/Policies/Mozilla/Thunderbird`                   | `username`         |
| `yandex_browser` | `yandex_browser_applier` | `Software/Policies/YandexBrowser`                      | `username`         |
| `firewall`       | `firewall_applier`    | `SOFTWARE\Policies\Microsoft\WindowsFirewall\FirewallRules` | -               |
| `gsettings`      | `gsettings_applier`   | `Software\BaseALT\Policies\gsettings`                     | `file_cache`       |
| `kde`            | `kde_applier`         | `Software/BaseALT/Policies/KDE`                           | -                  |
| `ntp`            | `ntp_applier`         | `Software\Policies\Microsoft\W32time\Parameters`          | -                  |
| `package`        | `package_applier`     | `Software\BaseALT\Policies\Packages`                      | -                  |
| `polkit`         | `polkit_applier`      | `Software\BaseALT\Policies\Polkit`                        | -                  |
| `systemd`        | `systemd_applier`     | `Software/BaseALT/Policies/SystemdUnits`                  | -                  |

---

## plugin

`gpoa_lib.plugin.plugin.plugin`

Abstract base class for all plugins (built-in and external).  Provides
`apply()`, `apply_user()`, `get_dict_registry()`, and structured logging.

### Constructor

```python
plugin(dict_dconf_db=None, username=None, fs_file_cache=None, registry_path=None)
```

| Parameter        | Type   | Description |
|-----------------|--------|-------------|
| `dict_dconf_db` | `dict` | Policy data (usually from `StorageAdapter.get_dict()` or `plugin_manager`). |
| `username`      | `str`  | Target username for user-scoped plugins. |
| `fs_file_cache` | object | File cache instance. |
| `registry_path` | `str`  | Custom registry subkey prefix for this plugin. |

### Methods

#### `apply(**kwargs)` *(final)*

Apply the plugin with current privileges.  Calls `self.run(**kwargs)`.

#### `apply_user(username, **kwargs)` *(final)*

Apply the plugin with user privileges using `with_privileges()`.

| Parameter  | Type  | Description |
|-----------|-------|-------------|
| `username` | `str` | User to run as. |

**Returns:** result of `run()` on success, `False` on failure.

#### `get_dict_registry(prefix='')` *(final)*

Get a dict from the registry for the given prefix.

| Parameter | Type  | Description |
|----------|-------|-------------|
| `prefix` | `str` | Registry key prefix. Default: `''` (all data). |

**Returns:** `dict`

#### `run(**kwargs)` *(abstract)*

The main plugin logic.  **Must** be overridden by subclasses.

#### `_init_plugin_log(message_dict=None, locale_dir=None, domain=None)`

Initialise the plugin-specific logger.

| Parameter       | Type   | Description |
|----------------|--------|-------------|
| `message_dict`  | `dict` | Mapping of message codes to format strings. |
| `locale_dir`    | `str`  | Path to locale directory. |
| `domain`        | `str`  | Gettext domain. |

#### `log(message_code, data=None)`

Log a message.  Uses the plugin-specific logger if initialised, otherwise
falls back to the global `log()`.

| Parameter       | Type   | Description |
|----------------|--------|-------------|
| `message_code`  | `str`  | Code like `'W1'`, `'E2'`, `'D134'`. |
| `data`          | `dict` | Context data for the message. |

### Attributes

| Attribute        | Type  | Description |
|-----------------|-------|-------------|
| `dict_dconf_db` | `dict` | Policy data. |
| `file_cache`    | object | File cache. |
| `username`      | `str`  | Target username. |
| `_registry_path` | `str` or `None` | Custom registry path prefix. |
| `plugin_name`   | `str`  | Class name (auto-set). |

---

## FrontendPlugin

`gpoa_lib.plugin.plugin_base.FrontendPlugin`

Base class for external frontend plugins.  Inherits from `plugin`.

Subclass this, implement `run()`, and install the module under
`/usr/lib/gpoa/plugins/`.  The plugin manager discovers and loads it
automatically.

### Constructor

```python
FrontendPlugin(dict_dconf_db=None, username=None, fs_file_cache=None, registry_path=None)
```

### Abstract Methods

#### `run(**kwargs)`

The main plugin logic.  **Must** be overridden.

### Example

```python
from gpoa_lib.plugin import FrontendPlugin

class MyPlugin(FrontendPlugin):
    def run(self, **kwargs):
        data = self.get_dict_registry('Software/MyOrg/Policies')
        for key, value in data.items():
            self.log('D1', {'key': key, 'value': value})

def create_machine_applier(dict_dconf_db, username, file_cache):
    return MyPlugin(dict_dconf_db, username, file_cache)

def create_user_applier(dict_dconf_db, username, file_cache):
    return MyPlugin(dict_dconf_db, username, file_cache)
```

---

## applier_frontend

`gpoa_lib.frontend.applier_frontend.applier_frontend`

Abstract base class for policy appliers.  Every applier inherits from this
ABC and must implement :meth:`apply`.

```python
class applier_frontend(ABC):
    def __init__(self, regobj):
        pass
    @abstractmethod
    def apply(self, **kwargs):
        raise NotImplementedError
```

| Parameter | Type   | Description |
|----------|--------|-------------|
| `regobj` | `Dconf_registry` | Registry storage object. |

### Helper functions (module-level)

```python
check_experimental_enabled(storage)    -> bool
check_windows_mapping_enabled(storage) -> bool
check_module_enabled(storage, module_name)     -> Optional[bool]
check_enabled(storage, module_name, is_experimental) -> bool
```

These helpers check registry flags in `Software/BaseALT/Policies/GPUpdate`
to determine whether an applier module should run.

---

## DualContextApplier

`gpoa_lib.frontend.applier_frontend.DualContextApplier`

Intermediate base class for appliers that need separate admin-context and
user-context execution phases.  Inherits from `applier_frontend`.

Use this when an applier runs different logic depending on whether it is
called with root privileges (admin context) or dropped user privileges
(user context).

### Methods

| Method | Description |
|--------|-------------|
| `admin_context_apply()` | Override to implement admin-privileged policy application. Default: `pass`. |
| `user_context_apply()` | Override to implement user-context policy application. Default: `pass`. |
| `apply()` | Calls `admin_context_apply()`. Do **not** override in subclasses. |

### Usage Example

```python
from gpoa_lib import DualContextApplier

class my_applier_user(DualContextApplier):
    def __init__(self, storage, username):
        self.storage = storage
        self.username = username

    def admin_context_apply(self):
        # runs as root
        pass

    def user_context_apply(self):
        # runs with user privileges
        pass
```

---

## plugin_manager

`gpoa_lib.plugin.plugin_manager.plugin_manager`

Internal class that discovers, loads, and runs plugins from
`/usr/lib/gpoa/plugins/` (external plugin path).

### Constructor

```python
plugin_manager(is_machine, username)
```

| Parameter    | Type  | Description |
|-------------|-------|-------------|
| `is_machine` | `bool` | `True` for machine context, `False` for user. |
| `username`   | `str`  | Target username. |

### Methods

#### `run()`

Execute all loaded plugins.  Uses `apply()` for machine context,
`apply_user()` for user context.

#### `load_plugins()`

Discover and instantiate plugins from the plugins directory.

**Returns:** `list[plugin]`

#### `get_plugin(name)`

Retrieve a loaded plugin instance by name.

| Parameter | Type  | Description |
|----------|-------|-------------|
| `name`   | `str` | Plugin class name. |

**Returns:** `plugin` instance or `None`.

---

## Dconf_registry

`gpoa_lib.storage.dconf_registry.Dconf_registry`

Low-level dconf registry access.  Uses **class-level** state (shared across
instances).  This class is used internally by the full gpupdate stack.
External consumers should prefer `StorageAdapter`.

### Key Class Methods

| Method | Description |
|--------|-------------|
| `get_key_value(key)` | Read a single key via `dconf read`. |
| `get_key_values(keys)` | Read multiple keys. |
| `get_matching_keys(path)` | Recursively list keys under a dconf path. |
| `get_dictionary_from_dconf_file_db(uid=None, path_bin=None, save_dconf_db=False)` | Read a GVdb binary database into a dict. |
| `dconf_update(uid=None, db_name=None)` | Compile dconf database. If `db_name` is given, compiles `/etc/dconf/db/{db_name}`; otherwise compiles `policy` (or `policy{uid}`). |
| `filter_entries(startswith, registry_dict=None)` | Filter the global registry dict by prefix. |
| `apply_template(uid)` | Write dconf profile for a user. |
| `set_info(key, data)` | Store metadata. |
| `get_info(key)` | Retrieve metadata. |

### Key Class Attributes

| Attribute | Description |
|-----------|-------------|
| `global_registry_dict` | Merged registry from all GPTs. |
| `_dconf_db` | Raw dconf database dict. |
| `_username` | Current username. |
| `_uid` | Current UID. |
| `_envprofile` | Profile environment (`'system'` or user). |

---

## GppStateManager

`gpoa_lib.storage.gpp_state.GppStateManager`

Manages GPP element lifecycle across gpupdate runs: `applyOnce`,
`removePolicy`, and GPO unlink cleanup.

### Constructor

```python
GppStateManager(username=None)
```

| Parameter  | Type  | Description |
|-----------|-------|-------------|
| `username` | `str` or `None` | User name; `None` or `'Machine'` for machine context. |

### Methods

#### `get_previous(element_type)`

Get previously applied elements for a given type.

| Parameter       | Type  | Description |
|----------------|-------|-------------|
| `element_type` | `str` | Element type name (e.g. `'Files'`, `'Shortcuts'`). |

**Returns:** `list[dict]`

---

#### `find_removed(element_type, current)`

Find elements removed since last run.

| Parameter       | Type        | Description |
|----------------|-------------|-------------|
| `element_type` | `str`       | Element type name. |
| `current`      | `list[dict]`| Current element list. |

**Returns:** `list[dict]`

---

#### `should_skip(element, element_type)`

Check if an element with `applyOnce` has already been applied.

| Parameter       | Type  | Description |
|----------------|-------|-------------|
| `element`      | `dict` | Element dictionary (must contain `uid` and `apply_once`). |
| `element_type` | `str`  | Element type name. |

**Returns:** `bool` -- `True` means the element should be skipped.

---

#### `mark_applied(element, element_type, element_obj=None)`

Mark an element as applied (timestamp is stored).

| Parameter      | Type  | Description |
|---------------|-------|-------------|
| `element`     | `dict` | Element dictionary. |
| `element_type`| `str`  | Element type name. |
| `element_obj` | object | Original element object to set `.applied` on. |

---

#### `cleanup_removed(element_type, current, handler)`

Find and clean up removed elements using the provided handler.

| Parameter       | Type        | Description |
|----------------|-------------|-------------|
| `element_type` | `str`       | Element type name. |
| `current`      | `list[dict]`| Current element list. |
| `handler`      | `callable`  | `handler(element_dict, username)` performing cleanup. |

### Module-level Functions

| Function | Description |
|----------|-------------|
| `get_previous_elements(element_type, username=None)` | Get previous elements from dconf. |
| `find_removed_elements(current, previous, key_field='uid')` | Diff current vs previous. |
| `find_gpo_removed_elements(current_gpos, previous_elements)` | Find elements from unlinked GPOs. |
| `is_element_applied(element, element_type, username=None)` | Check applyOnce status. |
| `mark_element_applied(element, element_type, username=None, element_obj=None)` | Mark applied. |
| `get_current_gpo_guids()` | Get currently linked GPO GUIDs. |
| `cleanup_file(element, username=None)` | Remove a deployed file. |
| `cleanup_shortcut(element, username=None)` | Remove a .desktop file. |
| `cleanup_folder(element, username=None)` | Remove a deployed folder. |
| `cleanup_envvar(element, username=None)` | Remove an environment variable. |
| `cleanup_inifile(element, username=None)` | Remove an INI setting. |

### Element Type Map

| Class Name      | Storage Name          |
|----------------|----------------------|
| `inifile`       | `Inifiles`           |
| `fileentry`     | `Files`              |
| `folderentry`   | `Folders`            |
| `shortcut`      | `Shortcuts`          |
| `drivemap`      | `Drives`             |
| `envvar`        | `Environmentvariables` |
| `networkshare`  | `Networkshares`      |
| `printer`       | `Printers`           |
| `service`       | `Services`           |

---

## DynamicAttributes / RegistryKeyMetadata

`gpoa_lib.storage.dynamic_attributes`

### DynamicAttributes

A generic attribute container that stores arbitrary key-value pairs and
sanitises string values (replaces quotes with double-prime characters).

```python
attr = DynamicAttributes(name='test', value=42)
attr.items()   # yields (key, value) pairs
dict(attr)     # convert to dict
```

#### Constructor

```python
DynamicAttributes(**kwargs)
```

#### Methods

| Method | Description |
|--------|-------------|
| `items()` | Iterate `(key, value)` pairs; `filters` is always last. |
| `get_original_value(key)` | Get value with quote restoration. |

---

### RegistryKeyMetadata

`DynamicAttributes` subclass storing metadata about a registry key.

```python
meta = RegistryKeyMetadata(
    policy_name='ControlPolicy',
    type='string',
    is_list=False,
    mod_previous_value=None,
)
```

#### Constructor

```python
RegistryKeyMetadata(policy_name, type, is_list=None, mod_previous_value=None)
```

| Parameter             | Type  | Description |
|----------------------|-------|-------------|
| `policy_name`        | `str` | Name of the policy. |
| `type`               | `str` | Value type (`'string'`, `'int'`, etc.). |
| `is_list`            | `bool` or `None` | Whether the value is a list. |
| `mod_previous_value` | any   | Previous value modifier. |

#### Attributes

| Attribute | Description |
|-----------|-------------|
| `policy_name` | Policy name. |
| `type` | Value type. |
| `reloaded_with_policy_key` | Set to `None` initially. |
| `is_list` | List flag. |
| `mod_previous_value` | Modifier. |

---

## Data Types

### PregDconf

`gpoa_lib.storage.dconf_registry.PregDconf`

Represents a single registry entry as extracted from dconf.

```python
PregDconf(keyname, valuename, type_preg, data)
```

| Attribute  | Type  | Description |
|-----------|-------|-------------|
| `keyname`  | `str` | Registry key path (without value name). |
| `valuename` | `str` | Value name. |
| `hive_key` | `str` | `keyname + '/' + valuename` (auto-generated). |
| `type`     | `int` | PREG type constant. |
| `data`     | any   | The actual value. |

### gplist

`gpoa_lib.storage.dconf_registry.gplist`

A `list` subclass with two convenience methods:

| Method | Description |
|--------|-------------|
| `first()` | Return the first element or `None`. |
| `count()` | Return `len(self)`. |

---

## Filters

`gpoa_lib.util.check_filters`

The `FilterChecker` class evaluates GPO targeting filters.  All check methods
are `@staticmethod` or `@classmethod` and accept `(filter_obj, username=None)`.

### FilterChecker

```python
from gpoa_lib.util.check_filters import FilterChecker
```

#### Static Check Methods

Each returns `bool` (`True` = filter passes).

| Method | Filter Class | Description | Key Attributes |
|--------|-------------|-------------|----------------|
| `check_computer` | `FilterComputer` | Match computer name | `name`, `type` (`'NETBIOS'` or `'DNS'`) |
| `check_domain` | `FilterDomain` | Match domain | `name`, `userContext` |
| `check_date` | `FilterDate` | Date matching | `period` (`'WEEKLY'`/`'MONTHLY'`/`'YEARLY'`), `dow`, `day`, `month`, `year` |
| `check_user` | `FilterUser` | Match username or SID | `name`, `sid` |
| `check_group` | `FilterGroup` | Match group membership | `name`, `sid`, `userContext` |
| `check_variable` | `FilterVariable` | Match environment variable | `variableName`, `value` |
| `check_time` | `FilterTime` | Time-of-day range | `begin`, `end` (ISO format) |
| `check_cpu` | `FilterCpu` | Minimum CPU speed | `speedMHz` |
| `check_battery` | `FilterBattery` | Check battery presence | (none) |
| `check_disk` | `FilterDisk` | Minimum free disk space | `drive` (`'%SystemDrive%'`), `freeSpace` (GB) |
| `check_language` | `FilterLanguage` | System/user locale | `language` (LCID), `default`, `system` |
| `check_ram` | `FilterRam` | Minimum RAM | `totalMB` |
| `check_file` | `FilterFile` | File/folder existence | `path`, `type` (`'EXISTS'`), `folder` (`'0'`/`'1'`) |
| `check_iprange` | `FilterIpRange` | IP address in range | `min`, `max`, `useIPv6` |
| `check_macrange` | `FilterMacRange` | MAC address in range | `min`, `max` |

#### Class Methods

| Method | Description |
|--------|-------------|
| `reset_cache()` | Clear all internal caches (call between GPO processing sessions). |

#### Module-level Function

```python
set_domain_resolver(resolver_func)
```

Override the domain resolution function.  Useful in tests or non-standard
environments.

---

## Utility Functions

`gpoa_lib.util.util`

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_machine_name()` | `() -> str` | Get the machine NetBIOS name (e.g. `DC0$`). |
| `is_machine_name(name)` | `(str) -> bool` | Check if a name is the machine name. |
| `get_homedir(username)` | `(str) -> str` | Get user's home directory path. |
| `get_user_info(username)` | `(str) -> pwd.struct_passwd` | Get passwd entry (cached). |
| `homedir_exists(username)` | `(str) -> bool` | Check home directory exists. |
| `mk_homedir_path(username, path)` | `(str, str) -> None` | Create subdirectory in user's home. |
| `string_to_literal_eval(string_)` | `(str) -> any` | Safely evaluate a string literal. |
| `get_uid_by_username(username)` | `(str) -> int` | Resolve username to UID. |
| `runcmd(command_name)` | `(list) -> (int, str)` | Run a command, return (rc, stdout). |
| `traverse_dir(root_dir)` | `(str) -> list[str]` | Recursively list files. |
| `utc_to_local(utc_str)` | `(str) -> str` | Convert UTC timestamp to local time. |

---

## Path Functions

`gpoa_lib.util.paths`

| Function | Returns | Description |
|----------|---------|-------------|
| `get_custom_policy_dir()` | `str` | `/etc/local-policy` |
| `local_policy_path(default_template_name='default')` | `Path` | Local policy template directory. |
| `cache_dir()` | `Path` | `/var/cache/gpupdate` |
| `file_cache_dir()` | `Path` | `/var/cache/gpupdate_file_cache` |
| `file_cache_path_home(username)` | `str` | `~user/.cache/gpupdate` |
| `local_policy_cache()` | `Path` | Cache directory for local policy. |
| `get_dconf_config_path(uid=None)` | `str` | dconf INI directory (`/etc/dconf/db/policy.d/` or `policy{uid}.d/`). |
| `get_dconf_config_file(uid=None)` | `str` | dconf INI file path. |
| `get_dconf_db_path(db_name)` | `str` | Path to INI directory for an arbitrary database (`/etc/dconf/db/{db_name}.d/`). |
| `get_dconf_db_file(db_name)` | `str` | Path to INI file for an arbitrary database (`/etc/dconf/db/{db_name}.d/{db_name}.ini`). |
| `gpupdate_plugins_path()` | `str` | Path to bundled frontend plugins. |
| `get_desktop_files_directory()` | `str` | `/usr/share/applications` |

### UNCPath

`gpoa_lib.util.paths.UNCPath`

Parses UNC (`\\server\share`) or URI (`smb://server/share`) paths.

| Method | Returns | Description |
|--------|---------|-------------|
| `get_uri()` | `str` | Convert to `smb://` URI. |
| `get_unc()` | `str` | Convert to `\\` UNC path. |
| `get_domain()` | `str` | Extract domain/server name. |
| `get_path()` | `str` | Extract path component. |
