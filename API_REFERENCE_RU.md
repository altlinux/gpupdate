# Справочник API gpoa_lib

Этот документ описывает все публичные классы и функции, экспортируемые пакетом
`gpoa_lib`.  Обзор высокого уровня см. в `README.md`; инструкции по разработке
плагинов --- в `PLUGIN_DEVELOPMENT_GUIDE.md`.

---

## Содержание

1. [Result](#result)
2. [StorageAdapter](#storageadapter)
3. [StorageWriter](#storagewriter)
4. [ApplierRunner](#applierrunner)
5. [plugin (абстрактный базовый класс)](#plugin)
6. [FrontendPlugin](#frontendplugin)
7. [plugin_manager](#plugin_manager)
8. [Dconf_registry](#dconf_registry)
9. [GppStateManager](#gppstatemanager)
10. [DynamicAttributes / RegistryKeyMetadata](#dynamicattributes--registrykeymetadata)
11. [Типы данных](#типы-данных)
12. [Фильтры (FilterChecker)](#фильтры)
13. [Вспомогательные функции](#вспомогательные-функции)
14. [Функции путей](#функции-путей)

---

## Быстрый импорт

```python
from gpoa_lib import (
    Result,
    StorageAdapter,
    StorageWriter,
    ApplierRunner,
    FrontendPlugin,
    applier_frontend,
    Dconf_registry,
    GppStateManager,
    DynamicAttributes,
    RegistryKeyMetadata,
)
```

---

## Result

`gpoa_lib.result.Result`

Типобезопасная обёртка возвращаемых значений для операций gpoa_lib.
Следует тому же шаблону, что и `Result` в Rust/Go: успешные операции
несут `data`, неудачные --- `error`.

### Конструктор

```python
Result(ok, data=None, error=None)
```

| Параметр | Тип    | Описание |
|----------|--------|----------|
| `ok`     | `bool` | Успешность операции. |
| `data`   | any    | Данные при успешном результате. |
| `error`  | `str`  | Описание ошибки при неудаче. |

### Методы класса

#### `Result.ok(data=None)`

Создать успешный результат.

**Возвращает:** `Result`

#### `Result.fail(error)`

Создать неудачный результат.

| Параметр | Тип                    | Описание |
|----------|------------------------|----------|
| `error`  | `str` или `Exception` | Описание ошибки. |

**Возвращает:** `Result`

### Атрибуты

| Атрибут | Тип    | Описание |
|---------|--------|----------|
| `ok`    | `bool` | `True` при успехе, `False` при неудаче. |
| `data`  | any    | Данные (имеют смысл только при `ok=True`). |
| `error` | `str`  | Строка ошибки (имеет смысл только при `ok=False`). |

### Использование

```python
result = runner.run('control')
if result:
    print('Применено:', result.data)
else:
    print('Ошибка:', result.error)
```

---

## StorageAdapter

`gpoa_lib.storage.storage_adapter.StorageAdapter`

Легковесный автономный читатель данных политик.  Загружает данные реестра из
бинарной базы dconf или из обычного словаря Python и предоставляет тот же
интерфейс запросов, который ожидают встроенные применители (`filter_hklm_entries`,
`get_entry` и т.д.).  В отличие от `Dconf_registry`, не хранит глобальное
состояние.

### Конструктор

```python
StorageAdapter(db_name=None, uid=None, prefix=None, keys=None, data=None)
```

| Параметр  | Тип         | Описание |
|-----------|-------------|----------|
| `db_name` | `str` или `None` | Имя файла базы данных в `/etc/dconf/db/`. |
| `uid`     | `int` или `None` | UID пользователя; при указании определяется пользовательский путь dconf. |
| `prefix`  | `str` или `None` | Префикс пути реестра; сохраняются только ключи под этим префиксом. |
| `keys`    | `list[str]` или `None` | Точные пути ключей реестра для извлечения. |
| `data`    | `dict` или `None` | Словарь для использования напрямую (без доступа к dconf). |

Должен быть указан **только один** из параметров `db_name` или `data`.  Не более
одного из `prefix` или `keys`.

### Фабричные методы

#### `StorageAdapter.from_dict(data)`

Создать адаптер из обычного словаря Python.

```python
adapter = StorageAdapter.from_dict({
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
    }
})
```

| Параметр | Тип    | Описание |
|----------|--------|----------|
| `data`   | `dict` | Вложенный словарь, сопоставляющий пути реестра с `{имя: значение}`. |

**Возвращает:** `StorageAdapter`

---

#### `StorageAdapter.from_dconf_db(db_name, uid=None)`

Загрузить данные политик из бинарной базы dconf.

```python
adapter = StorageAdapter.from_dconf_db('policy')
adapter = StorageAdapter.from_dconf_db('policy', uid=1000)
```

| Параметр  | Тип        | Описание |
|-----------|------------|----------|
| `db_name` | `str`      | Имя файла базы данных в `/etc/dconf/db/`. |
| `uid`     | `int`      | Необязательный UID пользователя для пользовательской базы. |

**Возвращает:** `StorageAdapter`

**Требует:** пакеты GObject Introspection для GVdb и GLib.

---

#### `StorageAdapter.from_dconf_db_prefix(db_name, prefix, uid=None)`

Загрузить из базы dconf, оставив только ключи под указанным префиксом.

```python
adapter = StorageAdapter.from_dconf_db_prefix('policy',
    'Software/BaseALT/Policies/Control')
```

| Параметр  | Тип        | Описание |
|-----------|------------|----------|
| `db_name` | `str`      | Имя файла базы данных в `/etc/dconf/db/`. |
| `prefix`  | `str`      | Префикс пути реестра для фильтрации. |
| `uid`     | `int`      | Необязательный UID пользователя. |

**Возвращает:** `StorageAdapter`

---

#### `StorageAdapter.from_dconf_db_keys(db_name, keys, uid=None)`

Загрузить из базы dconf, оставив только перечисленные ключи.

```python
adapter = StorageAdapter.from_dconf_db_keys('policy', [
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
    'Software/BaseALT/Policies/Control/ldap-tls-check',
])
```

| Параметр | Тип         | Описание |
|----------|-------------|----------|
| `db_name` | `str`      | Имя файла базы данных в `/etc/dconf/db/`. |
| `keys`    | `list[str]` | Точные пути ключей реестра для извлечения. |
| `uid`     | `int`      | Необязательный UID пользователя. |

**Возвращает:** `StorageAdapter`

---

### Методы запросов

#### `filter_hklm_entries(startswith)`

Возвращает список объектов `PregDconf`, имя ключа которых начинается с
`startswith`.  Завершающий символ `%` в `startswith` удаляется перед
сопоставлением.

```python
for entry in adapter.filter_hklm_entries('Software/BaseALT/Policies/Control'):
    print(entry.keyname, entry.valuename, entry.data)
```

| Параметр     | Тип    | Описание |
|-------------|--------|----------|
| `startswith` | `str`  | Префикс пути реестра. Завершающий `%` допускается и удаляется. |

**Возвращает:** `list[PregDconf]`

---

#### `filter_hkcu_entries(startswith)`

Псевдоним для `filter_hklm_entries`.  Адаптер не различает кусты HKLM / HKCU.

**Возвращает:** `list[PregDconf]`

---

#### `filter_entries(startswith)`

Псевдоним для `filter_hklm_entries`.

**Возвращает:** `list[PregDconf]`

---

#### `get_hklm_entry(hive_key)`

Получить одну запись в виде объекта `PregDconf`.

| Параметр   | Тип   | Описание |
|------------|-------|----------|
| `hive_key` | `str` | Полный путь реестра, напр. `Software/BaseALT/Policies/Control/sshd-gssapi-auth`. |

**Возвращает:** `PregDconf` или `None`

---

#### `get_hkcu_entry(hive_key)`

Псевдоним для `get_hklm_entry`.

**Возвращает:** `PregDconf` или `None`

---

#### `get_entry(path, preg=True)`

Получить одну запись или необработанное значение.

| Параметр | Тип    | Описание |
|----------|--------|----------|
| `path`   | `str`  | Полный путь реестра. Обратные слеши нормализуются. |
| `preg`   | `bool` | Если `True` (по умолчанию), возвращает `PregDconf`. Если `False` --- необработанное значение. |

**Возвращает:** `PregDconf` | any | `None`

---

#### `get_key_value(key)`

Сокращение для `get_entry(key, preg=False)`.

**Возвращает:** необработанное значение или `None`

---

#### `get_dict()`

Возвращает **глубокую копию** внутреннего словаря данных.  Безопасно передавать
в плагины или изменять без влияния на адаптер.

```python
data = adapter.get_dict()
# data --- независимая копия
```

**Возвращает:** `dict`

---

#### `check_enable_key(key)`

Проверяет, является ли значение ключа реестра «истинным».  Распознаёт строковые
значения `True`, `true`, `TRUE`, `yes`, `Yes`, `enabled`, `enable`, `Enabled`,
`Enable`, `1` и ненулевые целые числа.

**Возвращает:** `bool`

---

## StorageWriter

`gpoa_lib.storage.storage_writer.StorageWriter`

Записывает данные политик в произвольную базу dconf и компилирует её.

### Конструктор

```python
StorageWriter(db_name, uid=None, append=False)
```

| Параметр  | Тип    | Описание |
|-----------|--------|----------|
| `db_name` | `str`  | Имя базы данных в `/etc/dconf/db/`. Например, `'local'` записывает в `/etc/dconf/db/local.d/local.ini`. |
| `uid`     | `int`  | Необязательный UID пользователя для пользовательских баз. |
| `append`  | `bool` | Если `True`, дописать в существующий INI вместо перезаписи. По умолчанию `False`. |

### Методы

#### `write(data)`

Записать вложенный словарь `{секция: {ключ: значение}}` в INI-файл базы данных
и создать записи блокировок.

```python
writer = StorageWriter('local')
writer.write({
    'Software/BaseALT/Policies/Control': {
        'sshd-gssapi-auth': '1',
    }
})
writer.compile()
```

| Параметр | Тип    | Описание |
|----------|--------|----------|
| `data`   | `dict` | Вложенный словарь секций и пар ключ-значение. |

---

#### `write_keys(keys_dict)`

Записать плоский словарь `{полный_путь: значение}`.  Пути разделяются по
последнему `/` на секцию и имя значения.

```python
writer = StorageWriter('local')
writer.write_keys({
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth': '1',
    'Software/BaseALT/Policies/Control/ssh-gssapi-auth': 'enabled',
})
writer.compile()
```

| Параметр     | Тип    | Описание |
|--------------|--------|----------|
| `keys_dict`  | `dict` | Плоский словарь, сопоставляющий полные пути реестра со значениями. |

---

#### `delete_keys(keys)`

Удалить указанные ключи из INI-файла базы данных.  Перезаписывает файл,
исключая перечисленные ключи.

| Параметр | Тип         | Описание |
|----------|-------------|----------|
| `keys`   | `list[str]` | Полные пути реестра для удаления. |

---

#### `compile()`

Скомпилировать базу данных из INI-источников, выполнив `dconf compile`.

---

## ApplierRunner

`gpoa_lib.applier_runner.ApplierRunner`

Высокоуровневый фасад для создания и запуска встроенных применителей.
Обрабатывает создание `StorageAdapter`, внедрение дополнительных аргументов
(username, file_cache) и журналирование ошибок.

### Конструктор

```python
ApplierRunner(db_name=None, uid=None, data=None, force=False)
```

| Параметр  | Тип         | Описание |
|-----------|-------------|----------|
| `db_name` | `str` или `None` | Имя базы dconf (передаётся в `StorageAdapter`). |
| `uid`     | `int` или `None` | UID пользователя. |
| `data`    | `dict` или `None` | Словарь; при указании доступ к dconf не выполняется. |
| `force`   | `bool` | Если `True`, читать только из указанной базы (обход объединённого профиля) и повторно применять, даже если целевое состояние уже достигнуто. По умолчанию `False`. |

### Методы

#### `create(applier_name, prefix=None, keys=None)`

Создать экземпляр применителя без его запуска.

```python
runner = ApplierRunner(data=my_dict)
result = runner.create('control')
if result:
    applier = result.data
    applier.apply()
```

| Параметр        | Тип         | Описание |
|-----------------|-------------|----------|
| `applier_name`  | `str`       | Ключ во внутренней карте применителей (см. таблицу ниже). |
| `prefix`        | `str`       | Переопределить базовый префикс. Имя применителя добавляется автоматически: `prefix + '/' + applier_name`. |
| `keys`          | `list[str]` | Конкретные ключи реестра для загрузки. |

**Возвращает:** `Result` --- `result.data` содержит экземпляр применителя при успехе.

---

#### `run(applier_name, prefix=None, keys=None)`

Создать применитель и вызвать его метод `apply()`.  Исключения перехватываются
и возвращаются как неудачный `Result`.

```python
runner = ApplierRunner(data=my_dict)
result = runner.run('control')
if not result:
    print('Ошибка:', result.error)

runner.run('gsettings', prefix='Software/MyOrg')
```

**Возвращает:** `Result`

---

#### `resolve(key_or_prefix)`

Определить имя применителя по пути ключа реестра или префиксу.  Сравнение
нечувствительно к регистру и нормализует обратные слеши.

```python
>>> ApplierRunner.resolve('Software/BaseALT/Policies/Control/sshd-gssapi-auth')
'control'
>>> ApplierRunner.resolve('Software/Policies/Mozilla/Firefox')
'firefox'
>>> ApplierRunner.resolve('Software/Unknown/Path')
None
```

| Параметр        | Тип   | Описание |
|-----------------|-------|----------|
| `key_or_prefix` | `str` | Полный путь реестра или префикс. |

**Возвращает:** `str` или `None`

---

#### `run_auto(keys)`

Автоматически определить применитель по первому пути ключа и запустить его.

```python
runner = ApplierRunner(data=my_dict)
name = runner.run_auto([
    'Software/BaseALT/Policies/Control/sshd-gssapi-auth',
])
print(name)  # 'control'
```

| Параметр | Тип         | Описание |
|----------|-------------|----------|
| `keys`   | `list[str]` | Пути ключей реестра для применения. |

**Возвращает:** `str` или `None` --- имя запущенного применителя.

---

#### `list_appliers() -> list[str]`

Возвращает список доступных имён применителей.

```python
>>> ApplierRunner.list_appliers()
['control', 'chromium', 'firefox', 'thunderbird', 'yandex_browser',
 'firewall', 'gsettings', 'kde', 'ntp', 'package', 'polkit', 'systemd']
```

### Карта применителей

| Имя              | Класс                  | Ветка реестра                                              | Доп. аргументы     |
|-----------------|------------------------|------------------------------------------------------------|--------------------|
| `control`        | `control_applier`      | `Software/BaseALT/Policies/Control`                        | ---                |
| `chromium`       | `chromium_applier`     | `Software/Policies/Google/Chrome`                          | `username`         |
| `firefox`        | `firefox_applier`      | `Software/Policies/Mozilla/Firefox`                        | `username`         |
| `thunderbird`    | `thunderbird_applier`  | `Software/Policies/Mozilla/Thunderbird`                    | `username`         |
| `yandex_browser` | `yandex_browser_applier` | `Software/Policies/YandexBrowser`                       | `username`         |
| `firewall`       | `firewall_applier`     | `SOFTWARE\Policies\Microsoft\WindowsFirewall\FirewallRules` | ---              |
| `gsettings`      | `gsettings_applier`    | `Software\BaseALT\Policies\gsettings`                      | `file_cache`       |
| `kde`            | `kde_applier`          | `Software/BaseALT/Policies/KDE`                            | ---                |
| `ntp`            | `ntp_applier`          | `Software\Policies\Microsoft\W32time\Parameters`           | ---              |
| `package`        | `package_applier`      | `Software\BaseALT\Policies\Packages`                       | ---                |
| `polkit`         | `polkit_applier`       | `Software\BaseALT\Policies\Polkit`                         | ---                |
| `systemd`        | `systemd_applier`      | `Software/BaseALT/Policies/SystemdUnits`                   | ---                |

---

## plugin

`gpoa_lib.plugin.plugin.plugin`

Абстрактный базовый класс для всех плагинов (встроенных и внешних).
Предоставляет `apply()`, `apply_user()`, `get_dict_registry()` и
структурированное журналирование.

### Конструктор

```python
plugin(dict_dconf_db={}, username=None, fs_file_cache=None, registry_path=None)
```

| Параметр         | Тип    | Описание |
|------------------|--------|----------|
| `dict_dconf_db`  | `dict` | Данные политик (обычно из `StorageAdapter.get_dict()` или `plugin_manager`). |
| `username`       | `str`  | Ия пользователя для плагинов пользовательского контекста. |
| `fs_file_cache`  | object | Экземпляр файлового кэша. |
| `registry_path`  | `str`  | Пользовательский префикс пути реестра для этого плагина. |

### Методы

#### `apply(**kwargs)` *(final)*

Применить плагин с текущими привилегиями.  Вызывает `self.run(**kwargs)`.

#### `apply_user(username, **kwargs)` *(final)*

Применить плагин с привилегиями пользователя через `with_privileges()`.

| Параметр   | Тип   | Описание |
|------------|-------|----------|
| `username` | `str` | Пользователь, от имени которого выполняется запуск. |

**Возвращает:** результат `run()` при успехе, `False` при неудаче.

#### `get_dict_registry(prefix='')` *(final)*

Получить словарь из реестра для указанного префикса.

| Параметр | Тип   | Описание |
|----------|-------|----------|
| `prefix` | `str` | Префикс ключа реестра. По умолчанию: `''` (все данные). |

**Возвращает:** `dict`

#### `run(**kwargs)` *(abstract)*

Основная логика плагина.  **Должна** быть переопределена в подклассах.

#### `_init_plugin_log(message_dict=None, locale_dir=None, domain=None)`

Инициализировать журнализатор плагина.

| Параметр       | Тип    | Описание |
|----------------|--------|----------|
| `message_dict` | `dict` | Соответствие кодов сообщений строкам форматирования. |
| `locale_dir`   | `str`  | Путь к каталогу локализации. |
| `domain`       | `str`  | Домен gettext. |

#### `log(message_code, data=None)`

Записать сообщение в журнал.  Использует журнализатор плагина, если
инициализирован, иначе --- глобальный `log()`.

| Параметр       | Тип    | Описание |
|----------------|--------|----------|
| `message_code` | `str`  | Код, например `'W1'`, `'E2'`, `'D134'`. |
| `data`         | `dict` | Контекстные данные для сообщения. |

### Атрибуты

| Атрибут          | Тип   | Описание |
|------------------|-------|----------|
| `dict_dconf_db`  | `dict` | Данные политик. |
| `file_cache`     | object | Файловый кэш. |
| `username`       | `str`  | Ия пользователя. |
| `_registry_path` | `str` или `None` | Пользовательский префикс пути реестра. |
| `plugin_name`    | `str`  | Ия класса (устанавливается автоматически). |

---

## FrontendPlugin

`gpoa_lib.plugin.plugin_base.FrontendPlugin`

Базовый класс для внешних плагинов.  Наследуется от `plugin`.

Создайте подкласс, реализуйте `run()` и установите модуль в
`/usr/lib/gpoa/plugins/`.  Менеджер плагинов обнаружит и загрузит его
автоматически.

### Конструктор

```python
FrontendPlugin(dict_dconf_db={}, username=None, fs_file_cache=None, registry_path=None)
```

### Абстрактные методы

#### `run(**kwargs)`

Основная логика плагина.  **Должна** быть переопределена.

### Пример

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

## plugin_manager

`gpoa_lib.plugin.plugin_manager.plugin_manager`

Внутренний класс, который обнаруживает, загружает и запускает плагины из:
- `gpoa_lib/frontend_plugins/` (встроенные)
- `/usr/lib/gpoa/plugins/` (внешние)

### Конструктор

```python
plugin_manager(is_machine, username)
```

| Параметр     | Тип    | Описание |
|-------------|--------|----------|
| `is_machine` | `bool` | `True` для машинного контекста, `False` для пользовательского. |
| `username`   | `str`  | Ия целевого пользователя. |

### Методы

#### `run()`

Выполнить все загруженные плагины.  Использует `apply()` для машинного
контекста, `apply_user()` --- для пользовательского.

#### `load_plugins()`

Обнаружить и создать экземпляры плагинов из обоих каталогов.

**Возвращает:** `list[plugin]`

#### `get_plugin(name)`

Получить загруженный экземпляр плагина по имени.

| Параметр | Тип   | Описание |
|----------|-------|----------|
| `name`   | `str` | Ия класса плагина. |

**Возвращает:** экземпляр `plugin` или `None`.

---

## Dconf_registry

`gpoa_lib.storage.dconf_registry.Dconf_registry`

Низкоуровневый доступ к реестру dconf.  Использует состояние на уровне
**класса** (общее для всех экземпляров).  Этот класс используется внутри
полного стека gpupdate.  Внешним потребителям рекомендуется использовать
`StorageAdapter`.

### Основные методы класса

| Метод | Описание |
|-------|----------|
| `get_key_value(key)` | Прочитать один ключ через `dconf read`. |
| `get_key_values(keys)` | Прочитать несколько ключей. |
| `get_matching_keys(path)` | Рекурсивно вывести список ключей под путём dconf. |
| `get_dictionary_from_dconf_file_db(uid=None, path_bin=None, save_dconf_db=False)` | Прочитать бинарную базу GVdb в словарь. |
| `dconf_update(uid=None, db_name=None)` | Скомпилировать базу dconf. Если задан `db_name`, компилируется `/etc/dconf/db/{db_name}`; иначе --- `policy` (или `policy{uid}`). |
| `filter_entries(startswith, registry_dict=None)` | Фильтровать глобальный словарь реестра по префиксу. |
| `apply_template(uid)` | Записать профиль dconf для пользователя. |
| `set_info(key, data)` | Сохранить метаданные. |
| `get_info(key)` | Получить метаданные. |

### Основные атрибуты класса

| Атрибут | Описание |
|---------|----------|
| `global_registry_dict` | Объединённый реестр из всех GPT. |
| `_dconf_db` | Необработанный словарь базы dconf. |
| `_username` | Текущее имя пользователя. |
| `_uid` | Текущий UID. |
| `_envprofile` | Профиль окружения (`'system'` или пользователь). |

---

## GppStateManager

`gpoa_lib.storage.gpp_state.GppStateManager`

Управляет жизненным циклом элементов GPP между запусками gpupdate:
`applyOnce`, `removePolicy` и очистка при отвязке GPO.

### Конструктор

```python
GppStateManager(username=None)
```

| Параметр  | Тип            | Описание |
|-----------|----------------|----------|
| `username` | `str` или `None` | Ия пользователя; `None` или `'Machine'` для машинного контекста. |

### Методы

#### `get_previous(element_type)`

Получить ранее применённые элементы для заданного типа.

| Параметр       | Тип   | Описание |
|----------------|-------|----------|
| `element_type` | `str` | Ия типа элемента (напр. `'Files'`, `'Shortcuts'`). |

**Возвращает:** `list[dict]`

---

#### `find_removed(element_type, current)`

Найти элементы, удалённые с момента последнего запуска.

| Параметр       | Тип         | Описание |
|----------------|-------------|----------|
| `element_type` | `str`       | Ия типа элемента. |
| `current`      | `list[dict]` | Текущий список элементов. |

**Возвращает:** `list[dict]`

---

#### `should_skip(element, element_type)`

Проверить, был ли элемент с `applyOnce` уже применён.

| Параметр       | Тип   | Описание |
|----------------|-------|----------|
| `element`      | `dict` | Словарь элемента (должен содержать `uid` и `apply_once`). |
| `element_type` | `str`  | Ия типа элемента. |

**Возвращает:** `bool` --- `True` означает, что элемент следует пропустить.

---

#### `mark_applied(element, element_type, element_obj=None)`

Пометить элемент как применённый (сохраняется метка времени).

| Параметр       | Тип    | Описание |
|----------------|--------|----------|
| `element`      | `dict` | Словарь элемента. |
| `element_type` | `str`  | Ия типа элемента. |
| `element_obj`  | object | Исходный объект элемента для установки `.applied`. |

---

#### `cleanup_removed(element_type, current, handler)`

Найти и очистить удалённые элементы с помощью предоставленного обработчика.

| Параметр       | Тип         | Описание |
|----------------|-------------|----------|
| `element_type` | `str`       | Ия типа элемента. |
| `current`      | `list[dict]` | Текущий список элементов. |
| `handler`      | `callable`  | `handler(element_dict, username)` выполняет очистку. |

### Функции модульного уровня

| Функция | Описание |
|---------|----------|
| `get_previous_elements(element_type, username=None)` | Получить предыдущие элементы из dconf. |
| `find_removed_elements(current, previous, key_field='uid')` | Сравнить текущие и предыдущие элементы. |
| `find_gpo_removed_elements(current_gpos, previous_elements)` | Найти элементы из отвязанных GPO. |
| `is_element_applied(element, element_type, username=None)` | Проверить статус applyOnce. |
| `mark_element_applied(element, element_type, username=None, element_obj=None)` | Пометить как применённый. |
| `get_current_gpo_guids()` | Получить текущие привязанные GUID GPO. |
| `cleanup_file(element, username=None)` | Удалить развёрнутый файл. |
| `cleanup_shortcut(element, username=None)` | Удалить файл .desktop. |
| `cleanup_folder(element, username=None)` | Удалить развёрнутую папку. |
| `cleanup_envvar(element, username=None)` | Удалить переменную окружения. |
| `cleanup_inifile(element, username=None)` | Удалить настройку INI. |

### Соответствие типов элементов

| Ия класса       | Имя в хранилище       |
|-----------------|----------------------|
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

Универсальный контейнер атрибутов, хранящий произвольные пары ключ-значение и
санитизирующий строковые значения (заменяет кавычки на символы двойного штриха).

```python
attr = DynamicAttributes(name='test', value=42)
attr.items()   # возвращает пары (ключ, значение)
dict(attr)     # преобразовать в словарь
```

#### Конструктор

```python
DynamicAttributes(**kwargs)
```

#### Методы

| Метод | Описание |
|-------|----------|
| `items()` | Итерация пар `(ключ, значение)`; `filters` всегда последним. |
| `get_original_value(key)` | Получить значение с восстановлением кавычек. |

---

### RegistryKeyMetadata

Подкласс `DynamicAttributes`, хранящий метаданные о ключе реестра.

```python
meta = RegistryKeyMetadata(
    policy_name='ControlPolicy',
    type='string',
    is_list=False,
    mod_previous_value=None,
)
```

#### Конструктор

```python
RegistryKeyMetadata(policy_name, type, is_list=None, mod_previous_value=None)
```

| Параметр             | Тип   | Описание |
|----------------------|-------|----------|
| `policy_name`        | `str` | Ия политики. |
| `type`               | `str` | Тип значения (`'string'`, `'int'` и т.д.). |
| `is_list`            | `bool` или `None` | Является ли значение списком. |
| `mod_previous_value` | any   | Модификатор предыдущего значения. |

#### Атрибуты

| Атрибут | Описание |
|---------|----------|
| `policy_name` | Ия политики. |
| `type` | Тип значения. |
| `reloaded_with_policy_key` | Изначально `None`. |
| `is_list` | Флаг списка. |
| `mod_previous_value` | Модификатор. |

---

## Типы данных

### PregDconf

`gpoa_lib.storage.dconf_registry.PregDconf`

Представляет одну запись реестра, извлечённую из dconf.

```python
PregDconf(keyname, valuename, type_preg, data)
```

| Атрибут    | Тип   | Описание |
|------------|-------|----------|
| `keyname`  | `str` | Путь ключа реестра (без имени значения). |
| `valuename` | `str` | Ия значения. |
| `hive_key` | `str` | `keyname + '/' + valuename` (генерируется автоматически). |
| `type`     | `int` | Константа типа PREG. |
| `data`     | any   | Фактическое значение. |

### gplist

`gpoa_lib.storage.dconf_registry.gplist`

Подкласс `list` с двумя вспомогательными методами:

| Метод | Описание |
|-------|----------|
| `first()` | Вернуть первый элемент или `None`. |
| `count()` | Вернуть `len(self)`. |

---

## Фильтры

`gpoa_lib.util.check_filters`

Класс `FilterChecker` оценивает фильтры таргетинга GPO.  Все методы проверки ---
`@staticmethod` или `@classmethod` и принимают `(filter_obj, username=None)`.

### FilterChecker

```python
from gpoa_lib.util.check_filters import FilterChecker
```

#### Статические методы проверки

Каждый возвращает `bool` (`True` = фильтр пройден).

| Метод | Класс фильтра | Описание | Ключевые атрибуты |
|-------|--------------|----------|-------------------|
| `check_computer` | `FilterComputer` | Соответствие имени компьютера | `name`, `type` (`'NETBIOS'` или `'DNS'`) |
| `check_domain` | `FilterDomain` | Соответствие домену | `name`, `userContext` |
| `check_date` | `FilterDate` | Соответствие дате | `period` (`'WEEKLY'`/`'MONTHLY'`/`'YEARLY'`), `dow`, `day`, `month`, `year` |
| `check_user` | `FilterUser` | Соответствие пользователю или SID | `name`, `sid` |
| `check_group` | `FilterGroup` | Соответствие членству в группе | `name`, `sid`, `userContext` |
| `check_variable` | `FilterVariable` | Соответствие переменной окружения | `variableName`, `value` |
| `check_time` | `FilterTime` | Диапазон времени суток | `begin`, `end` (формат ISO) |
| `check_cpu` | `FilterCpu` | Минимальная частота ЦП | `speedMHz` |
| `check_battery` | `FilterBattery` | Наличие батареи | (нет) |
| `check_disk` | `FilterDisk` | Минимальное свободное место на диске | `drive` (`'%SystemDrive%'`), `freeSpace` (ГБ) |
| `check_language` | `FilterLanguage` | Локаль системы/пользователя | `language` (LCID), `default`, `system` |
| `check_ram` | `FilterRam` | Минимальный объём ОЗУ | `totalMB` |
| `check_file` | `FilterFile` | Существование файла/папки | `path`, `type` (`'EXISTS'`), `folder` (`'0'`/`'1'`) |
| `check_iprange` | `FilterIpRange` | IP-адрес в диапазоне | `min`, `max`, `useIPv6` |
| `check_macrange` | `FilterMacRange` | MAC-адрес в диапазоне | `min`, `max` |

#### Методы класса

| Метод | Описание |
|-------|----------|
| `reset_cache()` | Очистить все внутренние кэши (вызывать между сеансами обработки GPO). |

#### Функция модульного уровня

```python
set_domain_resolver(resolver_func)
```

Переопределить функцию разрешения домена.  Полезно в тестах или нестандартных
окружениях.

---

## Вспомогательные функции

`gpoa_lib.util.util`

| Функция | Сигнатура | Описание |
|---------|-----------|----------|
| `get_machine_name()` | `() -> str` | Получить NetBIOS-имя машины (напр. `DC0$`). |
| `is_machine_name(name)` | `(str) -> bool` | Проверить, является ли имя именем машины. |
| `get_homedir(username)` | `(str) -> str` | Получить путь к домашнему каталогу пользователя. |
| `get_user_info(username)` | `(str) -> pwd.struct_passwd` | Получить запись passwd (кэшируется). |
| `homedir_exists(username)` | `(str) -> bool` | Проверить существование домашнего каталога. |
| `mk_homedir_path(username, path)` | `(str, str) -> None` | Создать подкаталог в домашнем каталоге пользователя. |
| `string_to_literal_eval(string_)` | `(str) -> any` | Безопасно вычислить строковый литерал. |
| `get_uid_by_username(username)` | `(str) -> int` | Разрешить имя пользователя в UID. |
| `get_username_by_uid(uid)` | `(int) -> str` | Разрешить UID в имя пользователя. |
| `runcmd(command_name)` | `(list) -> (int, str)` | Выполнить команду, вернуть (код возврата, stdout). |
| `traverse_dir(root_dir)` | `(str) -> list[str]` | Рекурсивно получить список файлов. |
| `utc_to_local(utc_str)` | `(str) -> str` | Преобразовать метку времени UTC в локальное время. |

---

## Функции путей

`gpoa_lib.util.paths`

| Функция | Возвращает | Описание |
|---------|------------|----------|
| `get_custom_policy_dir()` | `str` | `/etc/local-policy` |
| `local_policy_path(template='default')` | `Path` | Каталог шаблона локальной политики. |
| `cache_dir()` | `Path` | `/var/cache/gpupdate` |
| `file_cache_dir()` | `Path` | `/var/cache/gpupdate_file_cache` |
| `file_cache_path_home(username)` | `str` | `~user/.cache/gpupdate` |
| `local_policy_cache()` | `Path` | Каталог кэша локальной политики. |
| `get_dconf_config_path(uid=None)` | `str` | Каталог INI dconf (`/etc/dconf/db/policy.d/` или `policy{uid}.d/`). |
| `get_dconf_config_file(uid=None)` | `str` | Путь к INI-файлу dconf. |
| `get_dconf_db_path(db_name)` | `str` | Путь к каталогу INI для произвольной базы данных (`/etc/dconf/db/{db_name}.d/`). |
| `get_dconf_db_file(db_name)` | `str` | Путь к INI-файлу для произвольной базы данных (`/etc/dconf/db/{db_name}.d/{db_name}.ini`). |
| `gpupdate_plugins_path()` | `str` | Путь к встроенным плагинам. |
| `get_desktop_files_directory()` | `str` | `/usr/share/applications` |

### UNCPath

`gpoa_lib.util.paths.UNCPath`

Разбирает пути UNC (`\\сервер\ресурс`) или URI (`smb://сервер/ресурс`).

| Метод | Возвращает | Описание |
|-------|------------|----------|
| `get_uri()` | `str` | Преобразовать в URI `smb://`. |
| `get_unc()` | `str` | Преобразовать в UNC-путь `\\`. |
| `get_domain()` | `str` | Извлечь домен/имя сервера. |
| `get_path()` | `str` | Извлечь компонент пути. |
