# Руководство по разработке плагинов GPOA

## Введение

GPOA (GPO Applier for Linux) поддерживает систему плагинов для расширения функциональности применения групповых политик.
Плагины позволяют добавлять поддержку новых типов политик и системных настроек без изменения основного кода.

## Архитектура плагинов

### Базовые классы

- **`plugin`** - Абстрактный базовый класс с финальными методами `apply()` и `apply_user()`
- **`FrontendPlugin`** - Упрощенный класс для плагинов с поддержкой логирования

### Менеджер плагинов

- **`plugin_manager`** - Загружает и выполняет плагины из директорий:
  - `/usr/lib/gpupdate/plugins/` - системные плагины
  - `gpoa/frontend_plugins/` - плагины разработки

## Создание простого плагина

### Пример: Базовый плагин с логированием

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
    Пример простого плагина с логированием и работой с реестром.
    """

    # Домен для переводов
    domain = 'example_applier'

    def __init__(self, dict_dconf_db, username=None, fs_file_cache=None):
        """
        Инициализация плагина.

        Args:
            dict_dconf_db (dict): Словарь с данными из реестра
            username (str): Имя пользователя
            fs_file_cache: Кэш файловой системы
        """
        super().__init__(dict_dconf_db, username, fs_file_cache)

        # Инициализация системы логирования
        self._init_plugin_log(
            message_dict={
                'i': {  # Информационные сообщения
                    1: "Example Applier initialized",
                    2: "Configuration applied successfully"
                },
                'w': {  # Предупреждения
                    10: "No configuration found in registry"
                },
                'e': {  # Ошибки
                    20: "Failed to apply configuration"
                }
            },
            domain="example_applier"
        )

    def run(self):
        """
        Основной метод выполнения плагина.

        Returns:
            bool: True если успешно, False при ошибке
        """
        try:
            self.log("I1")  # Плагин инициализирован

            # Получение данных из реестра
            self.config = self.get_dict_registry('Software/BaseALT/Policies/Example')

            if not self.config:
                self.log("W10")  # Конфигурация не найдена в реестре
                return True

            # Логирование данных из реестра
            self.log("I2")  # Конфигурация успешно применена

            return True

        except Exception as e:
            self.log("E20", {"error": str(e)})
            return False


def create_machine_applier(dict_dconf_db, username=None, fs_file_cache=None):
    """
    Фабричная функция для создания экземпляра плагина для машинного контекста.

    Args:
        dict_dconf_db (dict): Словарь с данными из реестра
        username (str): Имя пользователя
        fs_file_cache: Кэш файловой системы

    Returns:
        ExampleApplier: Экземпляр плагина
    """
    return ExampleApplier(dict_dconf_db, username, fs_file_cache)


def create_user_applier(dict_dconf_db, username=None, fs_file_cache=None):
    """
    Фабричная функция для создания экземпляра плагина для пользовательского контекста.

    Args:
        dict_dconf_db (dict): Словарь с данными из реестра
        username (str): Имя пользователя
        fs_file_cache: Кэш файловой системы

    Returns:
        ExampleApplier: Экземпляр плагина
    """
    return ExampleApplier(dict_dconf_db, username, fs_file_cache)
```

## Ключевые элементы плагина

### 1. Регистрация логов

Плагины используют систему логирования с кодами сообщений:

```python
self._init_plugin_log(
    message_dict={
        'i': {  # Информационные сообщения
            1: "Example Applier initialized",
            2: "Configuration applied successfully"
        },
        'w': {  # Предупреждения
            10: "No configuration found in registry"
        },
        'e': {  # Ошибки
            20: "Failed to apply configuration"
        }
    },
    domain="example_applier"
)
```

### 2. Работа с реестром

Доступ к данным из реестра через метод `get_dict_registry()`:

```python
self.config = self.get_dict_registry('Software/BaseALT/Policies/Example')
```

### 3. Вывод логов в методе run

Использование зарегистрированных кодов сообщений:

```python
self.log("I1")  # Простое сообщение
self.log("E20", {"error": str(e)})  # Сообщение с данными
```

### 4. Фабричные функции

Плагины должны предоставлять фабричные функции:

- `create_machine_applier()` - для машинного контекста
- `create_user_applier()` - для пользовательского контекста

## Система переводов

### Поддержка локализации

GPOA поддерживает автоматическую локализацию сообщений плагинов. Система использует стандарт GNU gettext.

### Структура файлов переводов

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

### Настройка переводов в плагине

1. **Определение домена переводов**:
```python
class MyPlugin(FrontendPlugin):
    domain = 'my_plugin'  # Домен для файлов перевода
```

2. **Инициализация логгера с поддержкой переводов**:
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
    domain="my_plugin"  # Домен для поиска файлов перевода
)
```

3. **Использование в коде**:
```python
# Сообщения автоматически переводятся при логировании
self.log("I1")  # Будет показано на языке системы
```

### Создание файлов перевода

1. **Извлечение строк для перевода**:
```bash
# Извлечь строки из кода плагина
xgettext -d my_plugin -o my_plugin.po my_plugin.py
```

2. **Создание файла перевода**:
```po
# my_plugin.po
msgid "Plugin initialized"
msgstr "Плагин инициализирован"

msgid "Configuration applied successfully"
msgstr "Конфигурация успешно применена"
```

3. **Компиляция переводов**:
```bash
# Скомпилировать .po в .mo
msgfmt my_plugin.po -o my_plugin.mo

# Разместить в правильной директории
mkdir -p /usr/share/locale/ru/LC_MESSAGES/
cp my_plugin.mo /usr/share/locale/ru/LC_MESSAGES/
```

### Лучшие практики для переводов

1. **Используйте полные предложения** - не разбивайте строки на части
2. **Избегайте конкатенации строк** - это затрудняет перевод
3. **Указывайте контекст** - добавляйте комментарии для переводчиков
4. **Тестируйте переводы** - проверяйте отображение на разных языках
5. **Обновляйте переводы** - при изменении сообщений обновляйте файлы .po

### Пример структуры плагина с переводами

```
my_plugin/
├── my_plugin.py          # Основной код плагина
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

## API плагинов

### Основные методы

- **`__init__(dict_dconf_db, username=None, fs_file_cache=None)`** - инициализация
- **`run()`** - основной метод выполнения (абстрактный)
- **`apply()`** - выполнение с текущими привилегиями (финальный)
- **`apply_user(username)`** - выполнение с привилегиями пользователя (финальный)
- **`get_dict_registry(prefix='')`** - получение данных из реестра
- **`_init_plugin_log(message_dict=None, locale_dir=None, domain=None)`** - инициализация логгера
- **`log(message_code, data=None)`** - логирование с кодами сообщений

### Система логирования

Коды сообщений:
- **I** - Информационные сообщения
- **W** - Предупреждения
- **E** - Ошибки
- **D** - Отладочные сообщения
- **F** - Фатальные ошибки

### Доступ к данным

- **`dict_dconf_db`** - словарь данных из реестра
- **`username`** - имя пользователя (для пользовательского контекста)
- **`fs_file_cache`** - кэш файловой системы для работы с файлами

## Контексты выполнения

### Машинный контекст

- Выполняется с правами root
- Применяет системные настройки
- Использует фабричную функцию `create_machine_applier()`

### Пользовательский контекст

- Выполняется с правами указанного пользователя
- Применяет пользовательские настройки
- Использует фабричную функцию `create_user_applier()`

## Лучшие практики

1. **Безопасность**: Всегда валидируйте входные данные
2. **Идемпотентность**: Повторное выполнение должно давать тот же результат
3. **Логирование**: Используйте коды сообщений для всех операций
4. **Обработка ошибок**: Плагин не должен "падать" при ошибках
5. **Транзакционность**: Изменения должны быть атомарными
6. **Переводы**: Поддерживайте локализацию сообщений
