from .applier_backend import applier_backend
import util

class local_policy_backend(applier_backend):
    __default_policy_path = '/usr/lib/python3/site-packages/gpoa/local-policy/default.xml'

    def __init__(self, username):
        self.username = username

    def get_values(self):
        policies = [util.load_xml_preg(self.__default_policy_path)]
        return policies

