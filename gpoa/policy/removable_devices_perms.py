from policy.common import Policy, Perms
from enum import Enum
import os

class DevType (Enum):
    CDDVD     = "{53f56308-b6bf-11d0-94f2-00a0c91efb8b}"
    FLOPPY    = "{53f56311-b6bf-11d0-94f2-00a0c91efb8b}"
    REMDISKS  = "{53f5630d-b6bf-11d0-94f2-00a0c91efb8b}"
    TAPEDRIVE = "{53f5630b-b6bf-11d0-94f2-00a0c91efb8b}"
    WPDDEV1   = "{6AC27878-A6FA-4155-BA85-F98F491D4F33}"
    WPDDEV2   = "{F33FDC04-D1AC-4E8E-9A30-19BBD4B108AE}"

class RemovableDevices (Policy):
    def __init__(self):
        self._Policy__name = "RemovebleDivicesPerms"
        self._Policy__script_name = "removable_devices_perms.sh"
        self._Policy__template = "removable_devices_perms.bash.j2"
        self._Policy__perms = Perms.ROOT

    def process(self, scope, path):
        print("{name} processing {path} ({scope})".format(name=self.name,path=path,scope=scope))
        perms = {}
        for p in os.listdir(path):
            if DevType(p) == DevType.REMDISKS:
                perms['Removable'] = self.__parse_perms('{}/{}'.format(path,p))
#            elif DevType(p) == DevType.CDDVD:

        perms['CDDVD'] = {'deny_exec': True, 'deny_read': False, 'deny_write': True}
        return (perms)

    def __parse_perms(self, path):
        deny_exec = self.__read_perm('{}/Deny_Execute.dword'.format(path))
        deny_read = self.__read_perm('{}/Deny_Read.dword'.format(path))
        deny_write = self.__read_perm('{}/Deny_Write.dword'.format(path))
        return ({'deny_exec': deny_exec, 'deny_read': deny_read, 'deny_write': deny_write})
    
    def __read_perm(self, path):
        try:
            f = open(path, 'r')
        except FileNotFoundError:
            return False
        
        p = f.read()
        if p == "0x00000001":
            return True
        else:
            return False

data_roots = {
    "Software/Microsoft/Windows/CurrentVersion/Policies/RemovableStorageDevices": RemovableDevices
}
