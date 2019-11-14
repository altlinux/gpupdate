import subprocess
import threading

class control:
    def __init__(self, name, value):
        self.control_name = name
        self.control_value = value
        self.possible_values = self._query_control_values()

    def _query_control_values(self):
        proc = subprocess.Popen(['sudo', 'control', self.control_name, 'list'], stdout=subprocess.PIPE)
        for line in proc.stdout:
            values = line.split()
            return values

    def get_control_name(self):
        return self.control_name

    def get_control_status(self):
        proc = subprocess.Popen(['sudo', 'control', self.control_name], stdout=subprocess.PIPE)
        for line in proc.stdout:
            return line.rstrip('\n\r')

    def set_control_status(self):
        print('Setting control {} to {}'.format(self.control_name, self.control_value))
        #proc = subprocess.Popen(['sudo', 'control', self.control_name, status], stdout=subprocess.PIPE)

