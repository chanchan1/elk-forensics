#!/usr/bin/env python
from pyVmomi import vim
from Utils import getObject
from Utils import str2bool
from Utils import getSpecFromXML

#order of preference
SUPPORTED_VIRTUAL_NW_DEVICES = [    vim.vm.device.VirtualVmxnet3,
                                    vim.vm.device.VirtualVmxnet2,
                                    vim.vm.device.VirtualE1000e,
                                    vim.vm.device.VirtualE1000,
                                    vim.vm.device.VirtualPCNet32 ]

# both add and remove NIC functions below can be merged into one function which takes an extra parameter "action"
# action could assume "add", "remove", change and other values.
# The function should return a vim.VirtualDeviceConfigSpec
def getNICDeviceKeyList(vmachine):
    # returns the key of the first network device found matching the network passed as parameter
    devices = vmachine.config.hardware.device
    if devices:
        networkDevices = [i for i in vmachine.config.hardware.device if type(i) in SUPPORTED_VIRTUAL_NW_DEVICES]

    networkDevKey = [device.key for device in networkDevices] # if device.backing.network.name == network]

    if networkDevices:
        return networkDevKey # careful, this is a list
    else:
        return None
        print "The VirtualMachine " + vmachine + " has 0 network devices?"

def deviceConfigSpecRemoveNIC(vmachine, network_device_key):
    # it's possible to remove a NIC based on other fields (key, deviceInfo.label)
    # however commonly VMs have a 1:1 - NIC:Network relationship,
    # therefore the NIC can be found by passing the network it's attached too
    if vmachine.runtime.powerState == "poweredON":
        print "For removing " + network + " network, the virtual machine should be powered Off"
        return None;

    config_spec_operation = vim.VirtualDeviceConfigSpecOperation('remove')
    deviceObj_List = [device for device in vmachine.config.hardware.device if device.key==int(network_device_key)]

    if len(deviceObj_List)==1:
        deviceObj = deviceObj_List[0]
        if(deviceObj):
            print "Removing NIC '" + deviceObj.deviceInfo.label + "' (key = " + str(network_device_key) + ") ..."
            devspec = vim.VirtualDeviceConfigSpec(operation=config_spec_operation, device=deviceObj)
            return devspec
    else:
        print "Failed - no clue"
        return None

def deviceConfigSpecAddNIC(vmachine, network):
    if vmachine.runtime.powerState == "poweredON":
        print "For adding " + network + " network, the virtual machine should be powered Off"
        return None;
    config_spec_operation = vim.VirtualDeviceConfigSpecOperation('add')
    backing_info = vim.VirtualEthernetCardNetworkBackingInfo(deviceName=network)
    device = vim.VirtualVmxnet3(key=-1,backing=backing_info)
    if(device):
        print "Adding NIC and attaching to network '" + network + "' ..."
        devspec = vim.VirtualDeviceConfigSpec(operation=config_spec_operation, device=device)
        return devspec

def getVirtualNWDeviceSpec(content, nw_spec_list, template):
    # this if can be removed, also "content" will be removed as it won't be used
    # motivation: we don't check for VM name when doing custom config, so why check if the network exists?
    # Leave it to the user or move it out to another function
    for nw_spec in nw_spec_list:
        target_network=nw_spec['name']
        if target_network:
            networkObject = getObject(content, [vim.Network], target_network)
            if networkObject:
                # New object which defines network backing for a virtual Ethernet card
                ## In case of several network device settings, we need to change the backing here to loop through the XML options
                ## otherwise all network devices will bind to target_network
                virtual_device_backing_info = vim.VirtualEthernetCardNetworkBackingInfo(network=networkObject,deviceName=target_network)
            else:
                print "Network name '" + target_network + "' not found."
                return None
        else:
            print "No network name was specified in the XML file or definition is invalid. . . ."
            return None

    # New object which contains information about connectable virtual devices
    # TODO: allowGuestControl and connected to be collected from XML?
    vdev_connect_info = vim.VirtualDeviceConnectInfo(startConnected=str2bool(nw_spec['startConnected']),allowGuestControl=False,connected=True)

    # get a list object containing the device key of all network devices associated with the VM
    networkDevkey_List = getNICDeviceKeyList(template)

    if networkDevkey_List:
        print "Found " + str(len(networkDevkey_List)) + " network device(s) in the template " + template.name
    else:
        print "Couldn't find any network device from " + template.name + " attached to " + target_network

    networkSpec = []
############ DEV
    # returns a list of Specs of devices to be deleted from the template  (if effectively removes all network devices)
    networkSpec_Remove = [deviceConfigSpecRemoveNIC(template,device_key) for device_key in networkDevkey_List]

    # add N network devices, N being the number of custom spec defined in the XML. This must match
    # loop through nw_spec_list, even if not using it (may be useful in the future)
    # there is no control here if the Network exists - nw_spec is taken directly from the XML file
    # TODO: check if all networks specified in the XML are indeed valid/existent networks
    networkSpec_Add = [deviceConfigSpecAddNIC(template, nw_spec['name']) for nw_spec in nw_spec_list]

    networkSpec = networkSpec_Remove + networkSpec_Add

############ WORKING - translated from PERL
#    # New object which define virtual device
#    print "debugging networkDevkey_List" + str(networkDevkey_List)
#    networkDevice_List = []
#    for device_key in networkDevkey_List:
#        networkDevice_List.append(vim.VirtualVmxnet3(key=device_key,
#                                        backing=virtual_device_backing_info,
#                                        connectable=vdev_connect_info))
#
#    # New object which encapsulates change specifications for an individual virtual device

#    for network_device in networkDevice_List:
#        networkSpec.append(vim.VirtualDeviceConfigSpec(operation=vim.VirtualDeviceConfigSpecOperation('edit'),device=network_device))

    return networkSpec
