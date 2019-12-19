import logging

from .adp import adp
from .exceptions import PluginInitError

class plugin_manager:
    def __init__(self):
        self.plugins = dict()
        logging.info('Starting plugin manager')
        try:
            self.plugins['adp'] = adp()
            logging.info('ADP plugin initialized')
        except PluginInitError as exc:
            self.plugins['adp'] = None
            logging.error(exc)

    def run(self):
        if self.plugins['adp']:
            self.plugins['adp'].run()

