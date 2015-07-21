#!/usr/bin/env python

from pyVmomi import vim
import xml.etree.ElementTree as ET

# it will parse the XML and return a dictionary with the OS  **OR** VM customization
# Accept:
#	spec_type  				OS-Spec, VM-Spec
#
#
# example:
# print getSpecFromXML('vmclone.xml', "OS-Spec")
#
# returns:
#
# {'domain': 'sec-cdc.local', 'auto_logon': '1', 'automode': 'perServer', 'ip': '192.168.111.111', 'hostname': 'testlin',
# 'orgnization_name': 'VMware', 'gateway': '192.168.111.1', 'domain_user_name': 'Administrator', 'netmask': '255.255.255.0',
# 'full_name': 'VMware', 'timezone': '100', 'domain_user_password': 'secret', 'cust_type': 'Linux', 'autousers': '5',
# 'productid': 'XXXX-XXXX-XXXX-XXXX-XXXX'}
#
SUPPORTED_XML_SPECS = [ 'OS-Spec',
                    'VM-Spec',
                    'Network-Spec']

SUPPORTED_VIRTUAL_NW_DEVICES = [    vim.vm.device.VirtualVmxnet2,
                                    vim.vm.device.VirtualVmxnet3,
                                    vim.vm.device.VirtualE1000,
                                    vim.vm.device.VirtualE1000e,
                                    vim.vm.device.VirtualPCNet32,
                                    vim.vm.device.VirtualVmxnet2    ]

# maybe using PropertyCollector in the future to look up Views
# http://www.geeklee.co.uk/object-properties-containerview-pyvmomi/
def findView(content, vimtype):
    objView = None
    objView = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    return objView

def getObject(content, vimtype, name):
	object = None
	container = findView(content, vimtype)
	for c in container.view: # a container can be a VirtualMachine, HostSystem, ResourcePool, Datastore etc
		if c.name == name:
			object = c
	return object

# aux function to convert some known string values to boolean
def str2bool(string):
  if string.lower() in ("yes", "true", "t", "1"):
    return True
  if string.lower() in ("no", "false", "f", "0"):
    return False

def getSpecFromXML(filename, spec_type):
  if spec_type in SUPPORTED_XML_SPECS:
    specList = []

    tree = ET.parse(filename)
    root = tree.getroot()
    spec = root.findall(spec_type)

    if spec is None:
      print "Couldn't find " + spec_type + " in " + filename + "."
    else:
      for element in spec:
          spec_dict = {}
          if len(element.attrib) == 1:
              spec_dict = element.attrib
          else:
              print "Error while parsing the XML. Spec should have only one attribute 'name'"
          for item in element:
              spec_dict[item.tag] = item.text
          specList.append(spec_dict)

    if len(specList) >= 1:
        if spec_type == "Network-Spec": # in this case we return the whole list with network specs
            return specList
        else:
            return specList[0]          # otherwise return a common list
  else:
    print "I don't understand this spec: " + spec_type + ". \nHint: the spec name is case sensitive."
    return None

# Totally messed up stuff :D
# https://www.vmware.com/support/developer/converter-sdk/conv55_apireference/vim.vm.customization.GlobalIPSettings.html
def customGlobalIPSettings(nw_spec_list):
        if len(nw_spec_list)>1:
            print "Multiple Network-Spec. That's okay - but choosing the first one for global DNS settings:"
            print "DNS Server List: ",
            print nw_spec_list[0]['dnsServerList'].split(":")
            print "DNS Suffix List: ",
            print nw_spec_list[0]['dnsSuffixList'].split(":")

        customization_global_settings = vim.CustomizationGlobalIPSettings(dnsServerList=nw_spec_list[0]['dnsServerList'].split(":"),
                                                                        dnsSuffixList=nw_spec_list[0]['dnsSuffixList'].split(":"))
        return customization_global_settings

def customSystemPreparation(os_spec):
    """
	TODO: this is the hostname, valid for Linux and Windows
	create a condition, if the
	"""
    if "SAME_AS_VM" == os_spec['hostName']:
            cust_name = vim.CustomizationVirtualMachineName()
    else:
            cust_name = vim.CustomizationFixedName(name=os_spec['hostName'])

	# test for Linux or Windows customization
    if (os_spec['custType'].lower() == "linux") or (os_spec['custType'].lower() == "lin"):
            cust_prep = vim.CustomizationLinuxPrep(domain=os_spec['joinDomain'],
												hostName=cust_name);

    elif (os_spec['custType'].lower() == "windows") or (os_spec['custType'].lower() == "win"):
            customization_identity_settings = vim.CustomizationIdentitySettings()
            customLicenseDataMode = vim.CustomizationLicenseDataMode(os_spec['autoMode'])

            cust_gui_unattended = vim.CustomizationGuiUnattended(autoLogon=str2bool(os_spec['autoLogon']),
                                                                autoLogonCount=0,
                                                                timeZone=int(os_spec['timeZone']));


            password = vim.CustomizationPassword(plainText=True, value=os_spec['domainAdminPassword'])
            cust_identification = vim.CustomizationIdentification(domainAdmin=os_spec['domainAdmin'],
                                                                domainAdminPassword=password,
                                                                joinDomain=os_spec['joinDomain'],
                                                                joinWorkgroup=os_spec['joinWorkgroup'])

            licenseFilePrintData = vim.CustomizationLicenseFilePrintData(autoMode=customLicenseDataMode,
            															autoUsers=int(os_spec['autoUsers']))

            cust_user_data = vim.CustomizationUserData(fullName=os_spec['fullName'],
        											orgName=os_spec['orgName'],
        											computerName=cust_name,
        											productId=os_spec['productId'])

            cust_prep = vim.CustomizationSysprep(guiUnattended=cust_gui_unattended,
    												identification=cust_identification,
    												licenseFilePrintData=licenseFilePrintData,
    												userData=cust_user_data);
    else:
    		print "The custType " + os_spec['custType'] + " is not suported. Quitting.."
    		exit

    return cust_prep

"""
TODO getCustomNICSettingMap
1) loop through to get all the interface configuration
maybe an idea is to add another Spec (Network-Spec) block into the XML
2) validate de IP address
"""
def customNICSettingMap(nw_spec_list):
    cust_adapter_mapping_list = []
    for nw_spec in nw_spec_list:
        if nw_spec['IP'] and nw_spec['IP'].lower() != "dhcp":
        	ip_address = vim.CustomizationFixedIp(ipAddress=nw_spec['IP'])
        elif nw_spec['IP'].lower() == "dhcp":
        	ip_address = vim.CustomizationDhcpIpGenerator()
        else:
        	print "Error while reading ip address ''" + nw_spec['IP'] + "' for customization. Quitting.."

        cust_ip_settings = vim.CustomizationIPSettings(ip=ip_address,
                      									gateway=nw_spec['gateway'],
                      									dnsServerList=nw_spec['dnsServerList'],
                      									subnetMask=nw_spec['subnetMask'],
                      									dnsDomain=nw_spec['dnsDomain'],
                      									primaryWINS=nw_spec['primaryWINS'],
                      									secondaryWINS=nw_spec['secondaryWINS'])
        cust_adapter_mapping_list.append(vim.CustomizationAdapterMapping(adapter=cust_ip_settings))
    return cust_adapter_mapping_list

def getOSCustomizationSpec(filename):
    customOSSpec = getSpecFromXML(filename, "OS-Spec")
    customNetworkSpecList = getSpecFromXML(filename, "Network-Spec")       # REMINDER: this is a list

    if customNetworkSpecList and customOSSpec:
        customization_spec = vim.CustomizationSpec(identity=customSystemPreparation(customOSSpec),
                                                    globalIPSettings=customGlobalIPSettings(customNetworkSpecList),
                                                    nicSettingMap=customNICSettingMap(customNetworkSpecList))
        return customization_spec

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


"""
def WaitForTasks(tasks, si):

   #Given the service instance si and tasks, it returns after all the
   #tasks are complete


   pc = si.content.propertyCollector

   taskList = [str(task) for task in tasks]

   # Create filter
   objSpecs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                                                            for task in tasks]
   propSpec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                         pathSet=[], all=True)
   filterSpec = vmodl.query.PropertyCollector.FilterSpec()
   filterSpec.objectSet = objSpecs
   filterSpec.propSet = [propSpec]
   filter = pc.CreateFilter(filterSpec, True)

   try:
      version, state = None, None

      # Loop looking for updates till the state moves to a completed state.
      while len(taskList):
         update = pc.WaitForUpdates(version)
         for filterSet in update.filterSet:
            for objSet in filterSet.objectSet:
               task = objSet.obj
               for change in objSet.changeSet:
                  if change.name == 'info':
                     state = change.val.state
                  elif change.name == 'info.state':
                     state = change.val
                  else:
                     continue

                  if not str(task) in taskList:
                     continue

                  if state == vim.TaskInfo.State.success:
                     # Remove task from taskList
                     taskList.remove(str(task))
                  elif state == vim.TaskInfo.State.error:
                     raise task.info.error
         # Move to next version
         version = update.version
   finally:
      if filter:
         filter.Destroy()
"""
