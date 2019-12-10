from .sqlite_registry import sqlite_registry
from .sqlite_cache import sqlite_cache

def cache_factory(cache_name):
    return sqlite_cache(cache_name)

def registry_factory(registry_name):
    return sqlite_registry(registry_name)

