'''
apstra_set_timers.py
    Used primarily for demos, this tool sets several Apstra service
    timers to shorter intervals, thus speeding up anomaly detection
    and reporting on the Apstra dashboard.  It is not intended for
    production, as the timer values are too short for networks larger
    than a few managed systems.  You should use this in conjunction
    with a configlet to speed up LLDP failure detection.  In Junos,
    it would look like this:

    protocols {
        lldp {
            advertisement-interval 5;
            hold-multiplier 3;
        }
    }
'''

import requests as req
import json
import getpass

from lib import apstra_utils as aosUtil

# Add this to suppress the InsecureRequestWarning
from urllib3.exceptions import InsecureRequestWarning

login_dict = { 'user': '', 'password': '', 'target': '', 'port': '' }

src_uuid = ''
system_list = []
service_timers = { 'bgp': 33, 'route': 33, 'interface': 10, 'lldp': 10 }

#########################
# Define some functions #
#########################

# Set the timers for a system
def set_timers( token, url, sys_id, service_timers ):
    base_url = url + '/systems/' + sys_id + '/services/'
    req_headers = { 'AUTHTOKEN': token }

    for k, v in service_timers.items():
        svc_url = base_url + k
        payload = { 'name': k, 'interval': v }

        print( 'Setting interval ' + str( v ) + 's for service ' + k )

        # Becasue bgp and route services require a POST before we can PUT...
        if k == 'bgp' or k == 'route':
            r = req.post( base_url, headers = req_headers, json = payload, verify=False )

        r = req.put( svc_url, headers = req_headers, json = payload, verify=False )

    return()


#
# Now for real
#
req.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
print( '\n\n' )
login_dict = aosUtil.parse_cmd_line()
login_dict = aosUtil.complete_login_dict( login_dict )

if login_dict[ 'port' ] == '443':
    base_url = 'https://' + login_dict[ 'target' ] + '/api'
else:
    base_url = 'https://' + login_dict[ 'target' ] + ':' + login_dict[ 'port' ] + '/api'

token = aosUtil.login( base_url, login_dict[ 'user' ], login_dict ['password' ] )

if token == '' :
    print( 'No valid authentication token.  Quitting...\n\n')
    quit()

aosUtil.get_bp_list( token, base_url )

while src_uuid == '':
    src_uuid = input( 'Enter UUID of desired blueprint: ' )
    src_data = aosUtil.get_bp_data( token, base_url, src_uuid )

system_list = aosUtil.get_systems_in_bp( token, base_url, src_uuid )

for system in system_list:
    print( 'Device: ' + str(system) )
    set_timers( token, base_url, system, service_timers )
    print ( '\n' )

aosUtil.logout( token, base_url )

quit()
