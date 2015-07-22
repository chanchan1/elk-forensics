#!/usr/bin/env python
from pyVmomi import vim
from Utils import getObject
from Utils import str2bool
from Utils import getSpecFromXML

# Totally messed up stuff :D
# https://www.vmware.com/support/developer/converter-sdk/conv55_apireference/vim.vm.customization.GlobalIPSettings.html
def customGlobalIPSettings(nw_spec_list):
        if len(nw_spec_list)>1:
            print "Multiple Network-Spec found. Choosing the first one for the global DNS settings:"
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
