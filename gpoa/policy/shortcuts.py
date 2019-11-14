from policy.common import Policy, Perms
import os
from pathlib import Path

class Shortcuts (Policy):
    def __init__(self):
        self._Policy__name = "Shortcuts"
        self._Policy__script_name = "shortcuts.sh"
        self._Policy__template = "shortcuts.bash.j2"
        self._Policy__perms = Perms.USER

    def process(self, scope, path):
        shortcuts = []
        print("{name} processing {path} ({scope})".format(name=self.name,path=path,scope=scope))
        for p in os.listdir(path):
            target_path = Path('{}/{}/targetPath'.format(path, p)).read_text()
            arguments = Path('{}/{}/arguments'.format(path, p)).read_text()
            shortcuts.append({'name': p, 'target': target_path, 'args': arguments}) 

        return ({'shortcuts': shortcuts})

data_roots = {
    "Preferences/Shortcuts": Shortcuts
}
