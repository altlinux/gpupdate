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

import logging

from .applier_frontend import applier_frontend
from .appliers.rpm import rpm

class package_applier(applier_frontend):
    def __init__(self, storage):
        self.storage = storage

    def apply(self):
        pass

class package_applier_user(applier_frontend):
    def __init__(self):
        pass

    def user_context_apply(self):
        '''
        There is no point to implement this behavior.
        '''
        pass

    def admin_context_apply(self):
        '''
        Install software assigned to specified username regardless
        which computer he uses to log into system.
        '''
        pass

