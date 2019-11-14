import policy.firewall
import policy.removable_devices_perms
import policy.printers
import policy.shortcuts
import policy.applications
from policy.common import Perms

data_roots = {}
data_roots.update(policy.firewall.data_roots)
data_roots.update(policy.removable_devices_perms.data_roots)
data_roots.update(policy.printers.data_roots)
data_roots.update(policy.shortcuts.data_roots)
data_roots.update(policy.applications.data_roots)