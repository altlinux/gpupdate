#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2022 BaseALT Ltd.
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

def read_networkshares(networksharesxml):
    networkshares = list()

    for share in get_xml_root(networksharesxml):
        props = share.find('Properties')
        networkshare_obj = networkshare(props.get('name'))
        networkshare_obj.set_action(props.get('action', default='C'))
        networkshare_obj.set_path(props.get('path', default=None))
        networkshare_obj.set_all_regular(props.get('allRegular', default=None))
        networkshare_obj.set_comment(props.get('comment', default=None))
        networkshare_obj.set_limitUsers(props.get('limitUsers', default=None))
        networkshare_obj.set_abe(props.get('abe', default=None))
        networkshares.append(networkshare_obj)

    return networkshares

def merge_networkshares(storage, sid, networkshares_objects, policy_name):
    for networkshareobj in networkshares_objects:
        storage.add_networkshare(sid, networkshareobj, policy_name)

class networkshare:
    def __init__(self, name):
        self.name = name

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
