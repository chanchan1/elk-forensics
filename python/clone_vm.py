#!/usr/bin/env python
"""
Original code by Dann Bohn

Clone a VM from template, accepts custom configuration

TODO: threat errors if VM name already exists
"""
from pyVmomi import vim
from pyVim.connect import SmartConnect, Disconnect
import atexit
import argparse
import getpass
from DTCustoms import getOSCustomizationSpec
from DTCustoms import getVMConfigSpec
#from DTCustoms import WaitForTasks
from DTCustoms import getObject


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

    parser.set_defaults(power_on=True, )

    args = parser.parse_args()

    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password')

    return args


def wait_for_task(task):
    """ wait for a vCenter task to finish """
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            print "The task finished with error"
            print task.info
            task_done = True

def cloneVM(
        content,
        template,
        vm_name,
        si,
        datacenter_name,
        vm_folder,
        target_host,
        datastore_name,
        cluster_name,
        resource_pool,
        customize_os,
        customize_vm,
        filename,
        power_on):
    """
    Clone a VM from a template/VM, datacenter_name, vm_folder, datastore_name
    cluster_name, resource_pool, and power_on are all optional.
    """

    # if none git the first one
    datacenter = getObject(content, [vim.Datacenter], datacenter_name)
    targethost = getObject(content, [vim.HostSystem], target_host)
    cluster = getObject(content, [vim.ClusterComputeResource], cluster_name)

    if vm_folder:
        destfolder = getObject(content, [vim.Folder], vm_folder)
    else: # clone into the same folder where the template is
        destfolder = getObject(content, [vim.Folder], template.parent.name)

    if datastore_name:
        datastore = getObject(content, [vim.Datastore], datastore_name)
    else:
        datastore = getObject(
            content, [vim.Datastore], template.datastore[0].info.name)

    if resource_pool:
        resource_pool = getObject(content, [vim.ResourcePool], resource_pool)
    else:
        if cluster is not None:
            resource_pool = cluster.resourcePool
        elif target_host is not None:
            resource_pool = targethost.parent.resourcePool
        else:
            print "Unable to find a suitable resourcePool"

    if customize_os:
        custom_spec = getOSCustomizationSpec(filename)
    if customize_vm:                                                            # this does OS-Spec and Network-Spec (both)
        config_spec = getVMConfigSpec(content, filename, template, vm_name)         # this does VM-Spec

    # set relospec
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = resource_pool

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.powerOn = power_on

    if custom_spec:
        print "Setting up OS customization.."
        clonespec.customization = custom_spec
    if config_spec:
        print "Setting up VM customization.."
        clonespec.config = config_spec

    cloneVMtask = template.CloneVM_Task(folder=destfolder, name=vm_name, spec=clonespec)
    return cloneVMtask

def main():
    """
    Let this thing fly
    """
    args = getArgs()

    # connect this thing
    si = SmartConnect(
        host=args.host,
        user=args.user,
        pwd=args.password,
        port=args.port)
    # disconnect this thing
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    template = None

    template = getObject(content, [vim.VirtualMachine], args.template)

    if template:
        clonevmtask = cloneVM(   # programming 101: never put user input into fucntions :X need to filter this before
            content,
            template,
            args.vm_name,
            si,
            args.datacenter_name,
            args.vm_folder,
            args.target_host,
            args.datastore_name,
            args.cluster_name,
            args.resource_pool,
            args.customize_os,
            args.customize_vm,
            args.filename,
            args.power_on)
        print "Cloning VM..."
        wait_for_task(clonevmtask)
    else:
        print "Template not found."


#   tasks = [vm.PowerOn() for vm in vmList if vm.name in vmnames]
#    WaitForTasks(clonevmtask,si)

# start this thing
if __name__ == "__main__":
    main()
