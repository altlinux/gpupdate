#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2025 BaseALT Ltd.
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

from abc import abstractmethod
from .plugin import plugin

class FrontendPlugin(plugin):
    """
    Base class for external frontend plugins.

    Subclass this, implement :meth:`run`, and install the module under
    ``/usr/lib/gpoa/plugins/``.  The plugin manager discovers and loads
    it automatically.

    Parameters
    ----------
    dict_dconf_db : dict
        Policy data passed by the plugin manager.
    username : str, optional
        Target username.
    fs_file_cache : object, optional
        File cache instance.
    registry_path : str, optional
        Registry subkey prefix this plugin reads from.

    Example
    -------
    ::

        from gpoa_lib.plugin import FrontendPlugin

        class MyPlugin(FrontendPlugin):
            def run(self, **kwargs):
                data = self.get_dict_registry('Software/MyOrg/Policies')
                for key, value in data.items():
                    ...
    """

    def __init__(self, dict_dconf_db=None, username=None, fs_file_cache=None, registry_path=None):
        super().__init__(dict_dconf_db if dict_dconf_db is not None else {}, username, fs_file_cache, registry_path)

    @abstractmethod
    def run(self, **kwargs):
        """
        Abstract method that must be implemented by concrete plugins.
        This method should contain the main plugin execution logic.
        """
        pass




