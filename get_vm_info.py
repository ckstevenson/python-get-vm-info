#!/usr/bin/env python3

"""
This script assumes the ldap lookup and vmware authentication account belong to the same domain
"""

import re
import socket
import smtplib
import os.path
import csv
import mimetypes
import ldap
import argparse
import getpass
import atexit
from email.message import EmailMessage
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

# This script isn't a module, but I like the use of the following metadata
__author__ = "Cameron Stevenson"
__license__ = "MIT License"
__version__ = "0.2.1"
__maintainer__ = "Cameron Stevenson (GitHub: ckstevenson)"
__email__ = "cksteve@protonmail.com"

# Array for VMs
vms = []

path = '/tmp/inventory/'
#path = './inventory/'
if not os.path.exists(path):
    os.makedirs(path)

def get_args ():
    parser = argparse.ArgumentParser(description='Arguments needed to connect to vCenter')

    parser.add_argument('-H', '--host',
                        required=True,
                        action='store',
                        help='vCenter host')

    parser.add_argument('-u', '--user',
                        required=True,
                        nargs='?',
                        action='store',
                        help='User name to use when connecting to vcenter')

    parser.add_argument('-p', '--password',
                        nargs='?',
                        required=True,
                        action='store',
                        help='Password to use when connecting to vcenter')

    parser.add_argument('-m', '--mail',
                        action='store_true',
                        help='Mail the csv and ini files stored in /tmp/')

    parser.add_argument('--mail-sender',
                        required=False,
                        default=socket.gethostname(),
                        nargs='?',
                        action='store',
                        help='User name to use when sending mail')

    parser.add_argument('--mail-password',
                        nargs='?',
                        #default=args.password,
                        required=False,
                        action='store',
                        help='Password to use when sending mail')

    parser.add_argument('--mail-recipient',
                        nargs='?',
                        required=False,
                        action='store',
                        help='Password to use when sending mail')

    parser.add_argument('--smtp',
                        nargs='?',
                        required=False,
                        action='store',
                        help='SMTP server to use when sending mail')

    parser.add_argument('-s', '--search',
                        action='store',
                        default='all',
                        required=False,
                        help='Filter the VM lookups to VM names only [names-only] or to include all [all] relevant info (e.g., datacenter, cluster, vapp, network, esxi_host, etc)')

    parser.add_argument('--search-base',
                        action='store',
                        required=False,
                        help='ldap search base, e.g., ou=Sites,dc=example,dc=com')

    parser.add_argument('--ldap-user',
                        action='store',
                        required=False,
                        help='ldap user, e.g. CN=User,OU=Accounts,DC=example,DC=com')

#    parser.add_argument('-F', '--format-inventory',
#                        nargs='?',
#                        action='store',
#                        required=True,
#                        help='Choose the inventory format type: csv, stdout')

    args = parser.parse_args()

    return args

def get_vm_info(vm, cluster, esxi_host, vcenter_host, domain):
    summary = vm.summary
    version = vm.config.version
    template = 'true' if (vm.config.template) else 'false'
    name = summary.config.name
    guest = summary.config.guestFullName
    state = summary.runtime.powerState
    vapp = vm.parentVApp.name if hasattr(vm.parentVApp, 'name') else 'null'

    if summary.guest is not None:
        ip_address = summary.guest.ipAddress
        hostname = summary.guest.hostName
        tools_version = summary.guest.toolsStatus
    else:
        hostname = summary.config.hostName #if hasattr(summary.config, 'hostName') else 'null'

    hostname = hostname or 'null'# 'null' if hostname is None
    ip_address = ip_address or 'null' #if ip_address is None
    tools_version = tools_version or 'null' #if ip_address is None

    if hostname == 'null':
        ad_state = 'true' if ldap_lookup(name, domain) else 'false'
    else:
        ad_state = 'true' if ldap_lookup(hostname.replace('.' + domain,""), domain) else 'false'

    vm_dict={'name' : name, 
        'hostname' : hostname, 
        'ad_state' : ad_state,
        'ip' : ip_address, 
        'guest' : guest, 
        'compatibility_version' : version, 
        'vapp': vapp,
        'cluster' : cluster, 
        'esxi_host' : esxi_host, 
        'state' : state, 
        'tools' : tools_version, 
        'is_template' : template}

    vms.append(vm_dict)
    return 0

def ldap_lookup(name, domain):
    args = get_args()
    #split=domain.split('.')
    name = name.replace('(','\(')
    name = name.replace(')','\)')
    search_base = args.search_base
    username=args.ldap_user
    password=args.password
    l = ldap.initialize('ldap://' + domain)
    l.simple_bind_s(username,password)

    if l.search_s(search_base, ldap.SCOPE_SUBTREE, "name=%s"%name):
        return True
    else:
        return False

def mail_results(mail_sender,mail_recipient,smtp):
    message = EmailMessage()
    body = 'Attached are the vCenter inventory csv and ini files.'

    message['From'] = mail_sender
    message['To'] = mail_recipient
    message['Subject'] = 'vCenter Inventory Files'
    message.set_content(body)

    for f in os.listdir(path) or []:
        f = path+f
        with open(f, 'rb') as ap:
            message.add_attachment(ap.read(), maintype='text', subtype='plain',
            filename=os.path.basename(f))

    mail_server = smtplib.SMTP(smtp)
    #mail_server.login(mail_sender, mail_password)
    mail_server.send_message(message)
    mail_server.quit()

def main():
    args = get_args()
    domain = re.search('(?<=\.).*',args.host)
    domain = domain.group()
    vcenter_host = re.sub('\..*','',args.host)

    try:
        service_instance = connect.SmartConnectNoSSL(host=args.host, user=args.user, pwd=args.password)
        if not service_instance:
            print("Could not connect to the specified host")
            return -1

        atexit.register(connect.Disconnect, service_instance)
        content = service_instance.RetrieveContent()
        
        if args.search == 'all':
            children = content.rootFolder.childEntity
            for child in children:
                dc = child
                clusters = dc.hostFolder.childEntity
                for cluster in clusters:
                    hosts = cluster.host
                    for host in hosts:
                        virtual_machines = host.vm
                        for vm in virtual_machines:
                            get_vm_info(vm, cluster.name, host.summary.config.name, vcenter_host, domain)

        elif args.search == 'names-only':
            container = content.rootFolder 
            viewType = [vim.VirtualMachine]
            recursive = True
            containerView = content.viewManager.CreateContainerView(container, viewType, recursive)
            children = containerView.view

            for child in children:
                print(child.summary.config.name)
        else:
            print("Error: not a supported option")

    except vmodl.MethodFault as error:
        print("Caught vmodl fault: " + error.msg)
        return -1

    try:
        labels=['name','hostname','ad_state', 'ip', 'guest', 'compatibility_version', 'vapp', 'cluster', 'esxi_host', 'state', 'tools', 'is_template']
        with open(path + vcenter_host + '.csv','w') as f:
            writer = csv.DictWriter(f, fieldnames=labels)
            writer.writeheader()
            for vm in vms:
                writer.writerow(vm)
    except Exception as e: print (e)

    if args.mail:
        mail_results(args.mail_sender,args.mail_recipient,args.smtp)

# Start program
if __name__ == "__main__":
    main()
