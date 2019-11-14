from policy.common import Policy, Perms
import os
from pathlib import Path

class Firewall (Policy):
    def __init__(self):
        self._Policy__name = "Firewall"
        self._Policy__script_name = "firewall.sh"
        self._Policy__template = "firewall.bash.j2"
        self._Policy__perms = Perms.ROOT  
    
    def process(self, scope, path):
        print("{name} processing {path} ({scope})".format(name=self.name,path=path,scope=scope))
        zoneRules = {}
        for p in os.listdir(path):
            if path.split('/')[-1:] == ["WindowsFirewall"]:
                for zone in os.listdir(path):
                    print("processing {} prifile".format(zone))
                    zoneRules[zone] = self.__process_firewall_rules(zone, path)

        return ({'zoneRules': zoneRules})

    def __process_firewall_rules(self, zone, path):
        print("processing rules in {} zone".format(zone))
        base = "{}/{}".format(path, zone)
        openPortsPath = "GloballyOpenPorts"
        rules = {}
        if os.path.exists("{}/{}".format(base, openPortsPath)):
            listPath = "{}/{}/List".format(base, openPortsPath)
            openPorts = []
            for r in os.listdir(listPath):
                rule = Path('{}/{}'.format(listPath, r)).read_text()
                [port, proto, srcs, enabled, name] = rule.split(':')
                sources = srcs.split(',')
                openPorts.append({'proto': proto, 'port': port, 'sources': sources})
            rules['openPorts'] = openPorts
            
        return(rules)

#        for r in os.listdir("{}/{}".format(path,zone)):
#            print(r)

data_roots = {
    "Software/Microsoft/Windows/CurrentVersion/Policies/NetworkAccessProtection/ClientConfig": Firewall,
    "Software/Microsoft/Windows/CurrentVersion/Policies/WindowsFirewall": Firewall
}
