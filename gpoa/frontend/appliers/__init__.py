#! /usr/bin/env python3
import subprocess
import threading
import os
import jinja2

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
        print('Setting control {} to {}'.format(self.control_name, status))

        try:
            proc = subprocess.Popen(['control', self.control_name, status], stdout=subprocess.PIPE)
        except:
            print('Unable to set {} to {}'.format(self.control_name, status))

class polkit:
    __template_path = '/usr/lib/python3/site-packages/gpoa/templates'
    __policy_dir    = '/etc/polkit-1/rules.d'
    __template_loader = jinja2.FileSystemLoader(searchpath=__template_path)
    __template_environment = jinja2.Environment(loader=__template_loader)

    def __init__(self, template_name, arglist):
        self.template_name = template_name
        self.args = arglist
        self.infilename = '{}.rules.j2'.format(self.template_name)
        self.outfile = os.path.join(self.__policy_dir, '{}.rules'.format(self.template_name))

    def generate(self):
        template = self.__template_environment.get_template(self.infilename)
        text = template.render(**self.args)
        with open(self.outfile, 'w') as f:
            f.write(text)

