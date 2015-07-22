from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

# from DTCustoms import WaitForTasks
from auxiliaries.Utils import getObject

def add_pg(targethost, pgname, vswitch, vlan, content):
    network = getObject(content, [vim.HostSystem], targethost).configManager.networkSystem
    policy = vim.host.NetworkPolicy()
    host_pg_spec = vim.host.PortGroup.Specification(name=pgname, vlanId=vlan, vswitchName=vswitch, policy=policy)
    network.AddPortGroup(host_pg_spec)
    print "Done"
