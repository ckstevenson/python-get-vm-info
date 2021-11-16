# Get VM Information
This script uses pyvmomi to query VMware for VMs and related information. It then performs other tasks based on the CLI arguments given. It is still a work in progress, but generally finished for the task I have at hand.

Inspiration was take from https://github.com/vmware/pyvmomi-community-samples

## Features
* Output default informaiton to csv file, and output VM names only to stdout
* Quicker results when querying for VM names only by creating a container view
* ldap lookups to see if a given machine is in AD (Active Directory) when default search is performed
* Email default results csv file 

## Usage
docker run -it get\_vm\_info /usr/src/get\_vm\_info.py -u xyz -p xyz --ldap-user 'CN=example,OU=ou,DC=example,DC=com' --search-base 'ou=ou,dc=example,dc=com' -H xyz -m --smtp xyz --mail-sender xyz --mail-recipient xyz

## Todo
- [X] SMTP email and username
- [ ] Use threads to improve performance
- [ ] Better string sanitization when performing an ldap lookup
- [ ] Add config file functionality
- [ ] Option for writing csv file to stdout to pipe to non-default location
- [ ] Correct argument requirements, e.g., LDAP info only needed when pulling all VM info
