from policy.common import Policy, Perms
import os
from pathlib import Path

class Applications (Policy):
    def __init__(self):
        self._Policy__name = "Applications"
        self._Policy__script_name = "applications.sh"
        self._Policy__template = "applications.bash.j2"
        self._Policy__perms = Perms.ROOT

    def process(self, scope, path):
        applications = []
        print("{name} processing {path} ({scope})".format(name=self.name,path=path,scope=scope))
        for p in os.listdir(path):
            package_name = Path('{}/{}/packageName'.format(path, p)).read_text()
            product_name = Path('{}/{}/productName'.format(path, p)).read_text()
            applications.append({'uuid': p, 'package': package_name, 'name': product_name}) 

        return ({'applications': applications})

data_roots = {
    "Applications": Applications
}
