#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2024 BaseALT Ltd.
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


from configparser import ConfigParser

from .util import (
      get_backends
    , get_default_policy_name
)

class GPConfig:
    __config_path = '/etc/gpupdate/gpupdate.ini'

    def __init__(self, config_path=None):
        if config_path:
            self.__config_path = config_path

        self.full_config = ConfigParser()
        self.full_config.read(self.__config_path)

    def get_backend(self):
        '''
        Fetch the name of the backend from configuration file.
        '''
        if 'gpoa' in self.full_config:
            if 'backend' in self.full_config['gpoa']:
                if self.full_config['gpoa']['backend'] in get_backends():
                    return self.full_config['gpoa']['backend']

        return 'samba'

    def set_backend(self, backend_name='local'):
        self.full_config['gpoa']['backend'] = backend_name
        self.write_config()

    # This function is not expected corresponding "set_dc()" function
    # because we have no way to automatically determine such kind
    # of setting.
    def get_dc(self):
        '''
        Fetch Domain Controller from configuration file.
        '''
        if 'samba' in self.full_config:
            if 'dc' in self.full_config['samba']:
                return self.full_config['samba']['dc']

    def get_local_policy_template(self):
        '''
        Fetch the name of chosen Local Policy template from
        configuration file.
        '''
        if 'gpoa' in self.full_config:
            if 'local-policy' in self.full_config['gpoa']:
                return self.full_config['gpoa']['local-policy']

        return get_default_policy_name()

    def set_local_policy_template(self, template_name='default'):
        self.full_config['gpoa']['local-policy'] = template_name
        self.write_config()

    def write_config(self):
        with open(self.__config_path, 'w') as config_file:
            self.full_config.write(config_file)

