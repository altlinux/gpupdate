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


from .applier_backend import applier_backend
from storage import registry_factory
from gpt.gpt import get_local_gpt
from util.util import (
    get_machine_name
)
from util.sid import get_sid

class nodomain_backend(applier_backend):

    def __init__(self):
        domain = None
        machine_name = get_machine_name()
        machine_sid = get_sid(domain, machine_name, True)
        self.storage = registry_factory()
        self.storage.set_info('domain', domain)
        self.storage.set_info('machine_name', machine_name)
        self.storage.set_info('machine_sid', machine_sid)

        # User SID to work with HKCU hive
        self.username = machine_name
        self.sid = machine_sid

    def retrieve_and_store(self):
        '''
        Retrieve settings and strore it in a database
        '''
        # Get policies for machine at first.
        self.storage.wipe_hklm()
        self.storage.wipe_user(self.storage.get_info('machine_sid'))
        local_policy = get_local_gpt(self.sid)
        local_policy.merge_machine()
        local_policy.merge_user()

