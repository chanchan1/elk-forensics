"""
Clone a VM from template, accepts custom configuration from XML
TODO: threat errors if VM name already exists

Original code: https://github.com/vmware/pyvmomi-community-samples/blob/master/samples/clone_vm.py

"""
from pyVmomi import vim

from auxiliaries.OSCustomizationSpec import getOSCustomizationSpec
from auxiliaries.VMConfigSpec import getVMConfigSpec
from auxiliaries.Utils import getObject
from auxiliaries.Utils import getSpecFromXML

def cloneVM(
        content,
        template,
        vm_name,
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
    Clone a VM from a template/VM, vm_folder, datastore_name
    cluster_name, resource_pool, and power_on are all optional.
    """

    template = getObject(content, [vim.VirtualMachine], template)
    if not template:
        print "VM template '" + template + "' not found."

    if filename:
        customVMSpec = getSpecFromXML(filename, "VM-Spec")
        # if a name is not passed, fetch it from the XML file
        if vm_name is None and customVMSpec['name'] is not None:
            print "VM name '" + customVMSpec['name'] + "' fetched from '" + filename
            vm_name = customVMSpec['name']
        #if vm_name could not be defined (not passed nor found in the XML), quit
        elif customVMSpec['name'] is None and vm_name is None:
            print "Unable to continue without a name for the new VM machine."
            exit

        if customize_os:
            custom_spec = getOSCustomizationSpec(filename)
        if customize_vm:                                                            # this does OS-Spec and Network-Spec (both)
            config_spec = getVMConfigSpec(content, filename, template, vm_name)         # this does VM-Spec

    print "Cloning started from template: '" + template.name + "' ==> '" + vm_name + "'"


    # if none git the first one
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
