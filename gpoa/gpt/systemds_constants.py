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

import re

VALID_STATES = {'as_is', 'enable', 'disable', 'mask', 'unmask', 'preset'}
VALID_APPLY_MODES = {'always', 'if_exists', 'if_missing'}
VALID_POLICY_TARGETS = {'machine', 'user'}
VALID_EDIT_MODES = {'create', 'override', 'create_or_override'}
VALID_DEP_MODES = {'changed', 'presence_changed'}
NON_RESTARTABLE_TYPES = {'device', 'scope'}

DEFAULT_DROPIN_NAME = '50-gpo.conf'
DROPIN_NAME_RE = re.compile(r'^[A-Za-z0-9_.@-]{1,128}\.conf$')
UNIT_NAME_RE = re.compile(
    r'^[A-Za-z0-9:_.@-]{1,255}\.(service|socket|timer|path|mount|automount|swap|target|device|slice|scope)$'
)

MAX_RULES_PER_SCOPE = 512
MAX_DEPENDENCIES_PER_RULE = 32
MAX_DEPENDENCY_PATH_LEN = 4096
MAX_UNIT_FILE_SIZE = 128 * 1024
