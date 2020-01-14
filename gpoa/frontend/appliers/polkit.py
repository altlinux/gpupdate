#
# Copyright (C) 2019-2020 BaseALT Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import jinja2
import logging

from util.logging import slogm

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
        try:
            template = self.__template_environment.get_template(self.infilename)
            text = template.render(**self.args)

            with open(self.outfile, 'w') as f:
                f.write(text)

            logging.debug(slogm('Generated file {} with arguments {}'.format(self.outfile, self.args)))
        except Exception as exc:
            logging.error(slogm('Unable to generate file {} from {}'.format(self.outfile, self.infilename)))

