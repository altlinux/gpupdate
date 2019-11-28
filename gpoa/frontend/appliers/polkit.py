#! /usr/bin/env python3
import os
import jinja2
import logging

logging.basicConfig(level=logging.DEBUG)

class polkit:
    __template_path = '/usr/share/gpupdate/templates'
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
        logging.debug('Generated file {} with arguments {}'.format(self.outfile, self.args))

