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

from util.xml import get_xml_root

def read_services(service_file):
    '''
    Read Services.xml from GPT.
    '''
    services = list()

    for srv in get_xml_root(service_file):
        srv_obj = service(srv.get('name'))
        srv_obj.set_clsid(srv.get('clsid'))
        srv_obj.set_usercontext(srv.get('userContext'))

        props = srv.find('Properties')
        startup_type = props.get('startupType')
        srv_obj.set_servicename(props.get('serviceName'))
        srv_obj.set_serviceaction(props.get('serviceAction'))
        timeout = props.get('timeout')

        services.append(srv_obj)

    return services

class service:
    def __init__(self, name):
        self.unit = name
        self.servname = None
        self.serviceaction = None

    def set_clsid(self, clsid):
        self.guid = uid

    def set_usercontext(self, usercontext=False):
        ctx = False

        if usercontext in [1, '1', True]:
            ctx = True

        self.is_in_user_context = ctx

    def is_usercontext(self):
        return self.is_in_user_context

    def set_servicename(self, sname):
        self.servname = sname

    def set_servact(self, sact):
        self.serviceaction = sact

