from policy.common import Policy, Perms
import os

class Printers (Policy):
    def __init__(self):
        self._Policy__name = "Printers"
        self._Policy__script_name = "printers.sh"
        self._Policy__template = "printers.bash.j2"
        self._Policy__perms = Perms.ROOT
    
    def process(self, scope, path):
        print("{name} processing {path} ({scope})".format(name=self.name,path=path,scope=scope))
        shared_path = "{}/SharedPrinter".format(path)
        port_path   = "{}/PortPrinter".format(path)
        local_path  = "{}/LocalPrinter".format(path)
        printers = []
        if os.path.exists(shared_path):
            print("SharedPrinters")
        if os.path.exists(port_path):
            print("PortPrinters")
            for p in os.listdir(port_path):
                with open("{}/{}/ipAddress".format(port_path,p)) as f:
                    addr = f.read()
                with open("{}/{}/localName".format(port_path,p)) as f:
                    name = f.read()
                prns = {'name': name, 'addr': addr}
                printers.append(prns)

        if os.path.exists(local_path):
            print("LocalPrinters")

        return ({'printers': printers})

    @property
    def data_roots(self):
        return data_roots

data_roots = {
    "Preferences/Printers": Printers
}
