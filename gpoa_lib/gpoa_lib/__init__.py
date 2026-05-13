#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

from gpoa_lib.storage.dconf_registry import Dconf_registry
from gpoa_lib.storage.dynamic_attributes import DynamicAttributes, RegistryKeyMetadata
from gpoa_lib.storage.gpp_state import GppStateManager
from gpoa_lib.storage.storage_adapter import StorageAdapter
from gpoa_lib.frontend.applier_frontend import applier_frontend
from gpoa_lib.plugin.plugin_base import FrontendPlugin
from gpoa_lib.applier_runner import ApplierRunner
