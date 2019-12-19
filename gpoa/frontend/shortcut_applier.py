import logging

from .applier_frontend import applier_frontend
from gpt.shortcuts import json2sc
from util.windows import expand_windows_var

class shortcut_applier(applier_frontend):
    def __init__(self, storage, sid, username):
        self.storage = storage
        self.sid = sid
        self.username = username

    def get_shortcuts(self):
        shortcut_objs = self.storage.get_shortcuts(self.storage.get_info('machine_sid'))
        shortcuts = list()

        for sc_obj in shortcut_objs:
            sc = json2sc(sc_obj.shortcut)
            shortcuts.append(sc)

        return shortcuts

    def apply(self):
        shortcuts = self.get_shortcuts()
        if shortcuts:
            for sc in shortcuts:
                dest_abspath = expand_windows_var(sc.dest, self.username).replace('\\', '/') + '.desktop'
                logging.debug('Writing shortcut file to {}'.format(dest_abspath))
                sc.write_desktop(dest_abspath)
        else:
            logging.debug('No shortcuts to process for {}'.format(self.storage.get_info('machine_sid')))

