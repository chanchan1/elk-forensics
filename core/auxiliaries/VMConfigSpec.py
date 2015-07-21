#!/usr/bin/env python
from pyVmomi import vim
from Utils import getSpecFromXML
from NetworkDeviceCustomization import getVirtualNWDeviceSpec

def getVMConfigSpec(content, filename, template, vmname):
    customVMSpec = getSpecFromXML(filename, "VM-Spec")
    customNetworkSpecList = getSpecFromXML(filename, "Network-Spec")

    # the priority is the name in the XML
    if customVMSpec['name'] and vmname:
        print "VM name '" + customVMSpec['name'] + "' fetched from '" + filename + "'. Ignoring " + vmname
        vmname = customVMSpec['name']
    elif customVMSpec['name'] is None and vmname is None:
        print "Unable to continue without a name for the new VM machine."
        exit

    networkDeviceSpec_List = getVirtualNWDeviceSpec(content, customNetworkSpecList, template)

    # append here other specifications *multiple network specs, disk, floppy, cd, etc*
    device_config_spec = []
    for network_spec in networkDeviceSpec_List:
        device_config_spec.append(network_spec)

    # New object which encapsulates configuration settings when creating or reconfiguring a virtual machine
    vm_config_spec = vim.VirtualMachineConfigSpec(name=vmname,
                                                    memoryMB=long(customVMSpec['memoryMB']),
                                                    numCPUs=int(customVMSpec['numCPUs']),
                                                    deviceChange=device_config_spec)
    return vm_config_spec;
