"""Restore typed preferences from the last accepted, local policy database."""
from ast import literal_eval
from copy import deepcopy
from types import SimpleNamespace

from storage.dconf_registry import Dconf_registry
from util.logging import log
from .files import fileentry
from .folders import folderentry
from .inifiles import inifile
from .envvars import envvar
from .drives import drivemap
from .printers import printer
from .scriptsini import Script
from .networkshares import networkshare
from .services import service
from .shortcuts import shortcut, get_ttype


def load_cached_policy(username, uid, is_machine):
    data = Dconf_registry.get_dictionary_from_dconf_file_db(uid, strict=True)
    data = {k: v for k, v in data.items() if not k.startswith('Previous/')}
    prefix = 'Software/BaseALT/Policies/Preferences/' + ('Machine' if is_machine else username)
    classes = {'Files': fileentry, 'Folders': folderentry, 'Inifiles': inifile,
               'Environmentvariables': envvar, 'Drives': drivemap, 'Printers': printer,
               'Scripts': Script, 'Networkshares': networkshare, 'Services': service,
               'Shortcuts': shortcut}
    restored = {}
    for name, cls in classes.items():
        entries = data.get(prefix, {}).get(name, [])
        if isinstance(entries, str):
            entries = literal_eval(entries)
        if not isinstance(entries, list):
            raise ValueError('Invalid cached preferences: ' + name)
        objects = []
        for values in entries:
            if not isinstance(values, dict):
                raise ValueError('Invalid cached preference item: ' + name)
            if cls is shortcut and 'is_in_user_context' not in values:
                # Old caches omitted this field. Never guess a privileged context.
                log('W7', {'reason': 'Refresh required for cached shortcut context'})
                continue
            obj = cls.__new__(cls)
            obj.__dict__.update({k: deepcopy(v) for k, v in values.items()
                                 if not k.startswith('_') and not callable(getattr(cls, k, None))})
            if hasattr(obj, 'filters'):
                obj.filters = [SimpleNamespace(**f) for f in obj.filters]
            if cls is shortcut:
                obj.type = get_ttype(obj.type)
                obj.expanded_path = obj.desktop_file_template = None
            objects.append(obj)
        restored[name.lower()] = objects
    # Publish only after the entire cache has been decoded successfully.
    Dconf_registry.global_registry_dict = data
    Dconf_registry._gpt_read_flag = True
    Dconf_registry._dconf_db = deepcopy(data)
    Dconf_registry.global_registry_dict['Previous/' + prefix] = deepcopy(data.get(prefix, {}))
    for name, objects in restored.items():
        setattr(Dconf_registry, name, objects)
