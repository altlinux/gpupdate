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

"""
gpoa_lib --- standalone policy applier library.

Provides storage, appliers, and a plugin framework for applying Group
Policy settings in Linux environments.  Can be used independently of
the full gpupdate stack.

Quick start::

    from gpoa_lib import ApplierRunner, StorageAdapter

    # Run an applier from a plain dict (no dconf needed)
    runner = ApplierRunner(data={
        'Software/BaseALT/Policies/Control': {'sshd-gssapi-auth': '1'},
    })
    runner.run('control')

    # Or read from a dconf database
    storage = StorageAdapter.from_dconf_db('policy')
    for entry in storage.filter_hklm_entries('Software/BaseALT/Policies/Control'):
        print(entry.valuename, entry.data)

Public API
----------
StorageAdapter
    Read policy data from dconf databases or plain dicts.
StorageWriter
    Write policy data to arbitrary dconf databases and compile them.
ApplierRunner
    High-level facade for creating and running appliers.
Result
    Type-safe return wrapper for operations.
FrontendPlugin
    Base class for external plugins.
applier_frontend
    Base class for built-in appliers.
Dconf_registry
    Low-level dconf access.
GppStateManager
    GPP lifecycle management (applyOnce, removePolicy, disabled).
DynamicAttributes, RegistryKeyMetadata
    Dynamic registry key metadata.
"""

from gpoa_lib.storage.dconf_registry import Dconf_registry
from gpoa_lib.storage.dynamic_attributes import DynamicAttributes, RegistryKeyMetadata
from gpoa_lib.storage.gpp_state import GppStateManager
from gpoa_lib.storage.storage_adapter import StorageAdapter
from gpoa_lib.storage.storage_writer import StorageWriter
from gpoa_lib.result import Result
from gpoa_lib.frontend.applier_frontend import applier_frontend, DualContextApplier
from gpoa_lib.plugin.plugin_base import FrontendPlugin
from gpoa_lib.applier_runner import ApplierRunner
