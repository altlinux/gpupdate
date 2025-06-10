#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2020 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import jinja2

from util.logging import log

class polkit:
    __template_path = '/usr/share/gpupdate/templates'
    __policy_dir    = '/etc/polkit-1/rules.d'
    __template_loader = jinja2.FileSystemLoader(searchpath=__template_path)
    __template_environment = jinja2.Environment(loader=__template_loader)

    def __init__(self, template_name, arglist, username=None):
        self.template_name = template_name
        self.args = arglist
        self.username = username
        self.infilename = '{}.rules.j2'.format(self.template_name)
        if self.username:
            self.outfile = os.path.join(self.__policy_dir, '{}.{}.rules'.format(self.template_name, self.username))
        else:
            self.outfile = os.path.join(self.__policy_dir, '{}.rules'.format(self.template_name))

    def _is_empty(self):
        for key, item in self.args.items():
            if key == 'User':
                continue
            elif item:
                return False
        return True

    def generate(self):
        if self._is_empty():
            if os.path.isfile(self.outfile):
                os.remove(self.outfile)
            return
        try:
            template = self.__template_environment.get_template(self.infilename)
            text = template.render(**self.args)

            with open(self.outfile, 'w') as f:
                f.write(text)

            logdata = {}
            logdata['file'] = self.outfile
            logdata['arguments'] = self.args
            log('D77', logdata)
        except Exception as exc:
            logdata = {}
            logdata['file'] = self.outfile
            logdata['arguments'] = self.args
            log('E44', logdata)

