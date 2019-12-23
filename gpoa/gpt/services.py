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
        service_name = props.get('serviceName')
        service_action = props.get('serviceAction')
        timeout = props.get('timeout')

        services.append(srv_obj)

    return services

class service:
    def __init__(self, name):
        self.unit = name

    def set_clsid(self, clsid):
        self.guid = uid

    def set_usercontext(self, usercontext=False):
        ctx = False

        if usercontext in [1, '1', True]:
            ctx = True

        self.is_in_user_context = ctx

    def is_usercontext(self):
        return self.is_in_user_context

