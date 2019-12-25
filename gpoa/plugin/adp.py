import logging
import subprocess

from util.rpm import is_rpm_installed
from .exceptions import PluginInitError
from util.logging import slogm

class adp:
    def __init__(self):
        if not is_rpm_installed('adp'):
            raise PluginInitError('adp is not installed - plugin cannot be initialized')
        logging.info(slogm('ADP plugin initialized'))

    def run(self):
        try:
            logging.info('Running ADP plugin')
            subprocess.call(['/usr/bin/adp', 'fetch'])
            subprocess.call(['/usr/bin/adp', 'apply'])
        except Exception as exc:
            logging.error(slogm('Error running ADP'))
            raise exc

