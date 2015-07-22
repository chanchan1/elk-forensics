import argparse
import atexit
import getpass
import xml.etree.ElementTree as ET

from pyVim.connect import SmartConnect, Disconnect
from core.addPortgroupToHost import add_pg
from core.cloneVM import cloneVM
from auxiliaries.Utils import waitForTasks


def getArgs():
    """ Get arguments from CLI """
    parser = argparse.ArgumentParser(
        description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--host',
                        required=True,
                        action='store',
                        help='vSpehre service to connect to')
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
    parser.add_argument('--vm-folder',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the VMFolder you wish\
                            the VM to be dumped in. If left blank\
                            The datacenter VM folder will be used')

    parser.add_argument('--datastore-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Datastore you wish the VM to end up on\
                            If left blank, VM will be put on the same \
                            datastore as the template')

    parser.add_argument('--datacenter-name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you\
                            wish to use. If omitted, the first\
                            datacenter will be used.')

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
    parser.add_argument('--bonding',
                        required=False,
                        action='store',
                        default=None,
                        help='configure interfaces for bonding')

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

    ### create xml
    xmltree = ET.parse(args.filename)
    root = xmltree.getroot()
    networks = root.findall("Network-Spec")
    if len(networks)==4: #prepare interfaces for bonding
        for i,network in enumerate(networks):
            network.set("name", "Internal_NFS_Trunk_"+str(i+1)+"_"+args.incident)

    hostname = root.find("VM-Spec")
    hostname.set("name", "CDC-DAVE-"+args.incident)

    xmltree.write("data/tmp.xml")
    print("Customized XML")

    # add pgs DD
    for i in range(1, 5):
        add_pg("192.168.2.40", "Internal_NFS_Trunk_"+str(i)+"_"+args.incident, args.vswitch, int(args.vlan), content)

    ### clone vm DD
    clonevmtask = [cloneVM(  #vm_folder, datastore_name, cluster_name, resource_pool, and power_on are all optional.
                             content=content,
                             template="CDC-DAVE-GI",
                             vm_name="CDC-DAVE-"+args.incident,
                             target_host="192.168.2.40",
                             customize_os=True,
                             customize_vm=True,
                             filename="data/tmp.xml",
                             vm_folder=None,
                             datastore_name=None,
                             cluster_name=None,
                             resource_pool=None,
                             power_on=False)]
    print "Cloning VM..."
    waitForTasks(clonevmtask, si)
    print("Cloned VM")

'''
    ### clone vm AA
    clonevmtask = [cloneVM(  # programming 101: never put user input into fucntions :X need to filter this before
                             content=content,
                             template="CDC-ANNA-GI",
                             vm_name="CDC-ANNA-"+args.incident,
                             target_host="192.168.2.42",
                             customize_os=True,
                             customize_vm=True,
                             filename=args.filename,
                             vm_folder=None,
                             datastore_name=None,
                             cluster_name=None,
                             resource_pool=None,
                             power_on=False)]
    print "Cloning VM..."
    waitForTasks(clonevmtask, si)
'''
# configure vms

# start this thing
if __name__ == "__main__":
    main()