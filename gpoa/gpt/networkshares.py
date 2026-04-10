#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2026 BaseALT Ltd.
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

from util.xml import get_xml_root
from util.gpp_lifecycle import generate_networkshare_uid

from .dynamic_attributes import DynamicAttributes
from .filter import parse_filters


def read_networkshares(networksharesxml):
    networkshares = []

    for share in get_xml_root(networksharesxml):
        props = share.find('Properties')
        networkshare_obj = networkshare(props.get('name'))
        networkshare_obj.set_action(props.get('action', default='C'))
        networkshare_obj.set_path(props.get('path', default=None))
        networkshare_obj.set_all_regular(props.get('allRegular', default=None))
        networkshare_obj.set_comment(props.get('comment', default=None))
        networkshare_obj.set_limitUsers(props.get('limitUsers', default=None))
        networkshare_obj.set_abe(props.get('abe', default=None))
        networkshare_obj.set_disabled(share.get('disabled') == '1')

        # Lifecycle attributes
        networkshare_obj.set_uid(share.get('uid'))
        networkshare_obj.set_remove_policy(share.get('removePolicy') == '1')
        networkshare_obj.set_bypass_errors(share.get('bypassErrors') == '1')
        networkshare_obj.set_changed(share.get('changed'))

        # Check for FilterRunOnce
        filters = share.find('Filters')
        if filters is not None:
            run_once = filters.find('FilterRunOnce')
            networkshare_obj.set_apply_once(run_once is not None)
        else:
            networkshare_obj.set_apply_once(False)

        # Parse and add filters
        parsed_filters = parse_filters(share)
        if parsed_filters:
            networkshare_obj.filters = parsed_filters

        networkshares.append(networkshare_obj)

    return networkshares

def merge_networkshares(storage, networkshares_objects, policy_name, policy_guid=None):
    for networkshareobj in networkshares_objects:
        storage.add_networkshare(networkshareobj, policy_name, policy_guid)

class networkshare(DynamicAttributes):
    def __init__(self, name):
        self.name = name
        self.disabled = False
        self.uid = None
        self.remove_policy = False
        self.bypass_errors = False
        self.apply_once = False
        self.changed = None

    def set_action(self, action):
        self.action = action
    def set_path(self, path):
        self.path = path
    def set_all_regular(self, allRegular):
        self.allRegular = allRegular
    def set_comment(self, comment):
        self.comment = comment
    def set_limitUsers(self, limitUsers):
        self.limitUsers = limitUsers
    def set_abe(self, abe):
        self.abe = abe
    def set_disabled(self, disabled):
        self.disabled = disabled
    def set_uid(self, uid):
        if uid:
            self.uid = uid
        else:
            self.uid = generate_networkshare_uid(self)
    def set_remove_policy(self, remove_policy):
        self.remove_policy = remove_policy
    def set_bypass_errors(self, bypass_errors):
        self.bypass_errors = bypass_errors
    def set_apply_once(self, apply_once):
        self.apply_once = apply_once
    def set_changed(self, changed):
        self.changed = changed
