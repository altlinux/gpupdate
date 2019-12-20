import subprocess
import threading
import logging

class control:
    def __init__(self, name, value):
        self.control_name = name
        self.control_value = value
        self.possible_values = self._query_control_values()
        if self.possible_values == None:
            raise Exception('Unable to query possible values')

    def _query_control_values(self):
        proc = subprocess.Popen(['control', self.control_name, 'list'], stdout=subprocess.PIPE)
        for line in proc.stdout:
            values = line.split()
            return values

    def _map_control_status(self, int_status):
        str_status = self.possible_values[int_status].decode()
        return str_status

    def get_control_name(self):
        return self.control_name

    def get_control_status(self):
        proc = subprocess.Popen(['control', self.control_name], stdout=subprocess.PIPE)
        for line in proc.stdout:
            return line.rstrip('\n\r')

    def set_control_status(self):
        status = self._map_control_status(self.control_value)
        logging.debug('Setting control {} to {}'.format(self.control_name, status))

        try:
            proc = subprocess.Popen(['control', self.control_name, status], stdout=subprocess.PIPE)
        except:
            logging.error('Unable to set {} to {}'.format(self.control_name, status))

