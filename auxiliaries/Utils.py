#!/usr/bin/env python

from pyVmomi import vim, vmodl
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

def waitForTask(task):
    """ wait for a vCenter task to finish """
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return task.info.result

        if task.info.state == 'error':
            print "The task finished with error"
            print task.info
            task_done = True

def waitForTasks(tasks, si):

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
