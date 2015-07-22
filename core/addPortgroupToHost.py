import atexit
import getpass
import argparse

from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect

# from DTCustoms import WaitForTasks
from auxiliaries.Utils import getObject


def getArgs():
    """ Get arguments from CLI """
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSpehre service to connect to')
    parser.add_argument('-t', '--targethost',
                        required=True,
                        action='store',
                        help='vSpehre host which is changed')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='Username to use')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use')
    parser.add_argument('-v', '--vlan',
                        required=True,
                        action='store',
                        help='VLAN Tag to use')
    parser.add_argument('-g', '--pgname',
                        required=True,
                        action='store',
                        help='Port Group name to add')
    parser.add_argument('-w', '--vswitch',
                        required=True,
                        action='store',
                        help='vSwitch to use')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def add_pg(targethost, pgname, vswitch, vlan, content):
    network = getObject(content, [vim.HostSystem], targethost).configManager.networkSystem
    policy = vim.host.NetworkPolicy()
    host_pg_spec = vim.host.PortGroup.Specification(name=pgname, vlanId=vlan, vswitchName=vswitch, policy=policy)
    network.AddPortGroup(host_pg_spec)
    print "Done"


def main():
    args = getArgs()
    si = SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port)
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    add_pg(args.targethost, args.pgname, args.vswitch, args.vlan, content)

# start this thing
if __name__ == "__main__":
    main()
