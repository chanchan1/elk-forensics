import argparse
import atexit
import getpass
from pyVim.connect import SmartConnect,Disconnect
from core.addPortgroupToHost import add_pg


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

    parser.add_argument('-i', '--incident',
                        required=True,
                        action='store',
                        help='Name of incident')

    parser.add_argument('-w', '--vswitch',
                        required=True,
                        action='store',
                        help='vSwitch to use')

    parser.add_argument('-v', '--vm-name',
                        required=False,
                        action='store',
                        help='Name of the VM you wish to make')

    parser.add_argument('--template',
                        required=True,
                        action='store',
                        help='Name of the template/VM \
                            you are cloning from')

    parser.add_argument('--target-host',
                        required=True,
                        action='store',
                        help='Name of the target HOST \
                                the VM will be deployed')

    parser.add_argument('--vm-folder',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the VMFolder you wish\
                            the VM to be dumped in. If left blank\
                            The template VM folder will be used')

    parser.add_argument('--datastore-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Datastore you wish the VM to end up on\
                            If left blank, VM will be put on the same \
                            datastore as the template')

    parser.add_argument('--cluster-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the cluster you wish the VM to\
                            end up on. If left blank the first cluster found\
                            will be used')

    parser.add_argument('--resource-pool',
                        required=False,
                        action='store',
                        default=None,
                        help='Resource Pool to use. If left blank the first\
                            resource pool found will be used')

    parser.add_argument('--customize-os',
                        dest='customize_os',
                        required=False,
                        action='store_true',
                        help='Customize the OS based on xml file')

    parser.add_argument('--customize-vm',
                        dest='customize_vm',
                        required=False,
                        action='store_true',
                        help='Customize the VM based on the xml file')

    parser.add_argument('-f', '--filename',
                        required=False,
                        action='store',
                        help='The XML file to be used as template. \
                            There is no schema check yet, so XSD file is irrelevant.')

    parser.add_argument('--power-on',
                        dest='power_on',
                        required=False,
                        action='store_true',
                        help='power on the VM after creation')

    parser.add_argument('--no-power-on',
                        dest='power_on',
                        required=False,
                        action='store_false',
                        help='do not power on the VM after creation')

    parser.set_defaults(power_on=True, )

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args

def main():
    args = getArgs()
    si = SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port)
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()


    # add pgs
    for i in range(1, 4):
        add_pg(args.target_host, "Internal_NFS_Trunk_"+i+"_"+args.incident, args.vswitch, args.vlan, content)

    #clone vms


    #configure vms

# start this thing
if __name__ == "__main__":
    main()
