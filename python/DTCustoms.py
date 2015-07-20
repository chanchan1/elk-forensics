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
SUPPORTED_SPECS = ['OS-Spec', 'VM-Spec', 'Network-Spec']

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
  if spec_type in SUPPORTED_SPECS:
    spec_dict = {}
    tree = ET.parse(filename)
    root = tree.getroot()
    spec = root.find(spec_type)
    if spec is None:
      print "Couldn't find " + spec_type + " in " + filename + "."
    else:
      for item in spec:
        spec_dict[item.tag] = item.text
    return spec_dict
  else:
    print "I don't understand this spec: " + spec_type + ". \nHint: the spec name is case sensitive."
    return None

def getCustomGlobalIPSettings(nw_spec):
	print nw_spec['IP0dnsServerList']
	customization_global_settings = vim.CustomizationGlobalIPSettings(dnsServerList=nw_spec['IP0dnsServerList'].split(":"))
	return customization_global_settings

def getSystemPreparation(os_spec):
	customization_identity_settings = vim.CustomizationIdentitySettings()

	password = vim.CustomizationPassword(
      plainText=True, value=os_spec['domainAdminPassword'])

	cust_identification = vim.CustomizationIdentification(domainAdmin=os_spec['domainAdmin'],
                                                        domainAdminPassword=password,
                                                        joinDomain=os_spec['joinDomain'],
														joinWorkgroup=os_spec['joinWorkgroup'])
	"""
	TODO: this is the hostname, valid for Linux and Windows
	create a condition, if the
	"""
	if "SAME_AS_VM" == os_spec['name']:
		cust_name = vim.CustomizationVirtualMachineName()
	else:
		cust_name = vim.CustomizationFixedName(name=os_spec['name'])

	cust_user_data = vim.CustomizationUserData(fullName=os_spec['fullName'],
											orgName=os_spec['orgName'],
											computerName=cust_name,
											productId=os_spec['productId'])

	customLicenseDataMode = vim.CustomizationLicenseDataMode(os_spec['autoMode'])

	licenseFilePrintData = vim.CustomizationLicenseFilePrintData(autoMode=customLicenseDataMode,
															autoUsers=int(os_spec['autoUsers']))

	cust_gui_unattended = vim.CustomizationGuiUnattended(autoLogon=str2bool(
	os_spec['autoLogon']), autoLogonCount=0, timeZone=int(os_spec['timeZone']));

	# test for Linux or Windows customization
	if (os_spec['custType'].lower() == "linux") or (os_spec['custType'].lower() == "lin"):
		cust_prep = vim.CustomizationLinuxPrep(domain=os_spec['joinDomain'],
												hostName=cust_name);
	elif (os_spec['custType'].lower() == "windows") or (os_spec['custType'].lower() == "win"):
		cust_prep = vim.CustomizationSysprep(guiUnattended=cust_gui_unattended,
												identification=cust_identification,
												licenseFilePrintData=licenseFilePrintData,
												userData=cust_user_data);
	else:
		print "The custType " + os_spec['custType'] + " is not suported. Quitting.."
		exit

	return cust_prep

def getCustomNICSettingMap(nw_spec):
	"""
	TODO:
	1) loop through to get all the interface configuration
	maybe an idea is to add another Spec (Network-Spec) block into the XML
	2) validate de IP address
	"""
	ip_address = nw_spec['IP0'];
	if ip_address and ip_address.lower() != "dhcp":
		customization_ip = vim.CustomizationFixedIp(ipAddress=ip_address)
	elif ip_address.lower() == "dhcp":
		customization_ip = vim.CustomizationDhcpIpGenerator()
	else:
		print "The ip address value " + ip_address + " is not suported. Quitting.."

	cust_ip_settings = vim.CustomizationIPSettings(ip=customization_ip,
	              									gateway=nw_spec['IP0gateway'],
	              									dnsServerList=nw_spec['IP0dnsServerList'],
	              									subnetMask=nw_spec['IP0subnetMask'],
	              									dnsDomain=nw_spec['IP0dnsDomain'],
	              									primaryWINS=nw_spec['IP0primaryWINS'],
	              									secondaryWINS=nw_spec['IP0secondaryWINS'])

	cust_adapter_mapping = vim.CustomizationAdapterMapping(adapter=cust_ip_settings)

	cust_adapter_mapping_list = [cust_adapter_mapping]

	return cust_adapter_mapping_list

def getOSCustomization(filename):
	customOSSpec = getSpecFromXML(filename, "OS-Spec")
	customNetworkSpec = getSpecFromXML(filename, "Network-Spec")

	customization_spec = vim.CustomizationSpec(identity=getSystemPreparation(customOSSpec),
	            									globalIPSettings=getCustomGlobalIPSettings(customNetworkSpec),
													nicSettingMap=getCustomNICSettingMap(customNetworkSpec))
	return customization_spec;

def setNetworkDevice(content, vm, nw_spec):
    network_dev_key = None;
    devices = template.config.hardware.device
    for dev in devices:
        if type(dev) is vm.device.VirtualVmxnet3 or
            type(dev) is vm.device.VirtualE1000 or
            type(dev) is vm.device.VirtualE1000e or
            type(dev) is vm.device.VirtualPCNet32 or
            type(dev) is vm.device.VirtualVmxnet2:
                network_dev_key = dev.key

    target_network=nw_spec['IP0Network']
    if target_network:
        network_view = getObject(content, [vim.Network], target_network)
       # New object which defines network backing for a virtual Ethernet card
       virtual_device_backing_info = vim.VirtualEthernetCardNetworkBackingInfo(network=network_view,
                                                                                deviceName=target_network)
    else: #not sure what's gonna happen here :D
        virtual_device_backing_info = vim.VirtualEthernetCardNetworkBackingInfo()


   # New object which contains information about connectable virtual devices
   vdev_connect_info = vim.VirtualDeviceConnectInfo(startConnected=str2bool(nw_spec['IP0startConnected']),
                                                        allowGuestControl=False,
                                                        connected=True);
   # New object which define virtual device
   network_device = vim.VirtualVmxnet3(key => $network_dev_key,
                                       backing => $virtual_device_backing_info,
                                       connectable => $vdev_connect_info);

   # New object which encapsulates change specifications for an individual virtual device
   my @device_config_spec = VirtualDeviceConfigSpec->new(
                                                     operation => VirtualDeviceConfigSpecOperation->new('edit'),
                                                     device => $network_device);

   # New object which encapsulates configuration settings when creating or reconfiguring a virtual machine
   my $vm_config_spec = VirtualMachineConfigSpec->new(
                                                  name => $vmname,
                                                  memoryMB => $memory,
                                                  numCPUs => $num_cpus,
                                                  deviceChange => \@device_config_spec);
   return $vm_config_spec;





def getVMSpecification(filename)
    customVMSpec = getSpecFromXML(filename, "VM-Spec")
    customNetworkSpec = getSpecFromXML(filename, "Network-Spec")

    network = customNetworkSpec['IP0Network']


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
