import logging

from .adp import adp
from .exceptions import PluginInitError
from util.logging import slogm

class plugin_manager:
    def __init__(self):
        self.plugins = dict()
        logging.info(slogm('Starting plugin manager'))
        try:
            self.plugins['adp'] = adp()
            logging.info(slogm('ADP plugin initialized'))
        except PluginInitError as exc:
            self.plugins['adp'] = None
            logging.error(slogm(exc))

    def run(self):
        if self.plugins['adp']:
            self.plugins['adp'].run()

