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

import configparser
import os
from ipalib import api

class ipaopts:
    def __init__(self):
        """Initialize the class and load the FreeIPA config file."""
        self.config_file = "/etc/ipa/default.conf"
        self.config = configparser.ConfigParser()

        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file for Freeipa{self.config_file} not found.")

        self.config.read(self.config_file)

    def get_realm(self):
        """Return the Kerberos realm from the config."""
        try:
            return self.config.get('global', 'realm')
        except (configparser.NoSectionError, configparser.NoOptionError):
            raise ValueError("Realm not found in config file.")

    def get_domain(self):
        """Return the domain from the config."""
        try:
            return self.config.get('global', 'domain')
        except (configparser.NoSectionError, configparser.NoOptionError):
            raise ValueError("Domain not found in config file.")

    def get_server(self):
        """
        Return the FreeIPA PDC Emulator server from API.
        Заменяет получение из config на динамический вызов API.
        """
        try:
            try:
                result = api.Command.gpmaster_show_pdc()
                pdc_server = result['result']['pdc_emulator']
                return pdc_server

            except Exception as api_error:
                print(api_error)

        except Exception as e:
            pass

    def get_machine_name(self):
        """Return the host from the config."""
        try:
            return self.config.get('global', 'host')
        except (configparser.NoSectionError, configparser.NoOptionError):
            raise ValueError("Host not found in config file.")

    def get_cache_dir(self):
        """Return the cache directory path."""
        return "/var/cache/freeipa/gpo_cache"
