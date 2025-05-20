'''
apstra_utils.py
    Library of handy fucntions for working with Apstra
'''

import argparse as ap
import requests as req
import json
import getpass

# Add this to suppress the InsecureRequestWarning
from urllib3.exceptions import InsecureRequestWarning

###########################
# Miscellaneous utilities #
###########################

#
# Parse the command line
#
def parse_cmd_line():
    login_dict = { 'user': '', 'password': '', 'target': '', 'port': '' }

    parser = ap.ArgumentParser( description = 'Generate property sets for SRX blueprint.' )
    parser.add_argument( '-u', '--user', type=str, help='Apstra username' )
    parser.add_argument( '-p', '--password', type=str, help='Apstra password' )
    parser.add_argument( '-t', '--target', type=str, help='IP/hostname of Apstra instance' )
    parser.add_argument( '-P', '--port', type=str, help='TCP port of Apstra instance (default 443)' )
    args = parser.parse_args()

    if args.user:
        login_dict[ 'user' ] = args.user
    if args.password:
        login_dict[ 'password' ] = args.password
    if args.target:
        login_dict[ 'target' ] = args.target
    if args.port:
        login_dict[ 'port' ] = args.port

    return login_dict

#
# Ensure there are no empties in the login dictionary
#
def complete_login_dict( login_dict ):
    while login_dict[ 'user' ] == '':
        login_dict[ 'user' ] = input( 'API username: ' )

    while login_dict[ 'password' ] == '':
        login_dict[ 'password' ] = getpass.getpass( 'Password: ' )
    
    while login_dict[ 'target' ] == '':
        login_dict[ 'target' ] = input( 'Target IP/Hostname: ' )
    
    while login_dict[ 'port' ] == '':
        login_dict[ 'port' ] = input( 'Target TCP Port: ' )

    return( login_dict )


########################################################
# Network operations: reachability, login/logout, etc. #
########################################################

#
# Make sure we can reach the target
def networkOK( url ):
    try:
        req.head( url, timeout = 10, verify=False )
        return True
    
    except req.ConnectionError:
        return False

#
# Login and grab token
def login( url, user, password ):
    if networkOK( url ):
        url = url + '/aaa/login'
        login_payload = { 'username': user, 'password': password }
        r = req.post( url, data = json.dumps(login_payload), verify=False )

        if r.status_code == 201:
            token = json.loads(r.text)['token']
            print( 'Login successful, got a token.\n')
    
        else:
            print( 'Login failed, got HTTP ' + str(r.status_code) +
                   ' error.  Quitting.\n' )
            token = ''
            quit()

    else:
        print( 'Can not reach AOS instance at ' + url + '.  Quitting.\n' )
        quit()
        
    return( token )

#
# Logout
def logout( token, url ):
    url = url + '/aaa/logout'
    req_headers = { 'AUTHTOKEN': token }
    logout_ok = False
    r = req.post( url, headers = req_headers, verify=False )

    if r.status_code == req.codes.ok:
        print('Successfully logged out from API.\n')
        logout_ok = True
    
    else:
        print('Clean logout from API failed.\n')
    
    return( logout_ok )


###############################
# Interacting with Blueprints #
###############################

#
# Get blueprint data as JSON
def get_bp_data( token, url, bp_uuid ):
    json_out = ''
    url = url + '/blueprints/' + bp_uuid
    req_headers = { 'AUTHTOKEN': token }
    r = req.get( url, headers=req_headers, verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Failed to grab JSON data for blueprint ' + bp_uuid + '.  Quitting.\n')
        quit()

    json_out = json.loads(r.text)
    print( 'Grabbing JSON data from ' + json_out[ 'label' ] + '...\n' )

    return json_out

#
# Get UUID of target blueprint
def get_bp_id( token, url, bp_name ):
    bp_id = ''
    req_headers = { 'AUTHTOKEN': token }
    r = req.get( url, headers = req_headers, verify=False )

    if r.status_code == req.codes.ok:
        json_out = json.loads(r.text)

        for bp in json_out['items']:
            if bp['label'] == bp_name:
                bp_id = bp['id']
                print('Got a match for ' + bp_name +
                      '.  UUID is ' + bp_id + '.\n')
                
        if bp_id == '':
            print( 'Error. No bluepirint found with name ' + bp_name +
                   '.  Quitting.' )
            quit()

    return( bp_id )

#
# Get a list of blueprints
def get_bp_list ( token, url ):
    url = url + '/blueprints'
    req_headers = { 'AUTHTOKEN': token }
    query_ok = False
    r = req.get( url, headers=req_headers, verify=False )

    if r.status_code == req.codes.ok:
        json_out = json.loads( r.text )
        print( '\nThis server contains the following blueprints:\n')
        print(f'{"BP Name":<24}' + 'UUID')
        print(f'{"-------":<24}' + '----')

        for bp in json_out[ 'items' ]:
            print(f'{bp[ 'label' ]:<24}' + bp[ 'id' ])
        print( '\n' )
        query_ok = True

    else:
        print( 'Could not get list of blueprints.\n' )
        
    return( query_ok )

#
# Get data from a single security zone (VRF) in a blueprint
def get_sz_data( token, url, bp_id, sz_id ):
    json_out = ''
    req_headers = { 'AUTHTOKEN': token }
    url = url + '/blueprints/' + bp_id + '/security-zones/' + sz_id
    r = req.get( url, headers = req_headers, verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Error getting security zone in ' + bp_id + '. Quitting.' )
        sys_list= []
        quit()

    json_out = json.loads(r.text)
    print( 'Getting security zone parameters from blueprint...\n' )

    return( json_out )

#
# Get data from a single VN in a blueprint
def get_vn_data( token, url, bp_id, vn_id ):
    json_out = ''
    req_headers = { 'AUTHTOKEN': token }
    url = url + '/blueprints/' + bp_id + '/virtual-networks/' + vn_id
    r = req.get( url, headers = req_headers, verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Error getting VN in ' + bp_id + '. Quitting.' )
        sys_list= []
        quit()

    json_out = json.loads(r.text)
    print( 'Getting VN parameters from blueprint...\n' )

    return( json_out )

#
# Get list of VN's from a blueprint as JSON
def get_vn_list( token, url, bp_uuid ):
    json_out = ''
    url = url + '/blueprints/' + bp_uuid + '/virtual-networks'
    req_headers = { 'AUTHTOKEN': token }
    r = req.get( url, headers=req_headers, verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Failed to get virtual network list for blueprint ' + bp_uuid + '.  Quitting.\n')
        quit()

    json_out = json.loads(r.text)
    print( 'Getting virtual network list from blueprint...\n' )

    return( json_out )

#
# Run a commit check on a blueprint
def commit_check( token, url, bp_uuid ):
    success = False
    check_url = url + '/blueprints/' + bp_uuid + '/commit-check'
    result_url = url + '/blueprints/' + bp_uuid + '/commit-check-result'
    req_headers = { 'AUTHTOKEN': token }

    print( 'Running commit-check on devices in blueprint...\n' )
    r = req.post( check_url, headers=req_headers, verify=False )

    if str(r.status_code)[ 0 ] == '2':
        print( 'Completed commit-check.  Verifying results...\n' )
        r = req.get( result_url, headers=req_headers, verify=False )

        if str(r.status_code)[ 0 ] == '2':
            print( 'Success!\n')
            success = True

        elif str(r.status_code) == '400':
            print( 'Rendered configuration failed commit-check on at least one device.' )
            print( 'Please review results in the Apstra IDE to identify errors.\n' )
            
        else:
            print( 'Error: The commit-check completed successfully, but there was an error validating results.' )
            print( 'Please check the Apstra logs before trying again.\n' )

    elif str(r.status_code) == '404':
        print( 'Error:  System missing from commit-check.\n' )

    elif str(r.status_code) == '409':
        print( 'Error:  Pending operation in queue.  Please try again.\n' )

    else:
        print( 'An error occurred.  Please check the Apstra logs before trying again.\n' )

    return( success )

#
# Deploy staged changes to a blueprint
def deploy_bp( token, url, bp_uuid ):
    success = False
    deploy_version = ''
    deploy_description = 'Configuration deployed by script.'

    deploy_version = get_deploy_status( token, url, bp_uuid ) + 1

    if deploy_version != '':
        url = url + '/blueprints/' + bp_uuid + '/deploy'
        req_headers = { 'AUTHTOKEN': token }

        deploy_payload = { 'version': deploy_version, 'description': deploy_description }
        print( 'Deploying version ' + str(deploy_version) + ' of blueprint...\n' )
        r = req.put( url, headers=req_headers,
                     data = json.dumps( deploy_payload), verify=False )
        
        if str(r.status_code)[ 0 ] == '2':
            success = True
            print( 'Deployed version ' + str(deploy_version) + ' of blueprint.\n' )

        elif str(r.status_code) == '404':
            print( 'Error: No blueprint with UUID ' + bp_uuid + ' found.\n' )
      
        else:
            print( 'Unspecified error.  Please check the Apstra logs for details.\n' )     

    else:
        print( 'Deploy of blueprint failed.\n' )

    return( success )

#
# Get deploy status of a blueprint
def get_deploy_status( token, url, bp_uuid ):
    deploy_version = ''
    url = url + '/blueprints/' + bp_uuid + '/deploy'
    req_headers = { 'AUTHTOKEN': token }

    print( 'Finding current database version of the blueprint...\n' )
    r = req.get( url, headers=req_headers, verify=False )

    if str(r.status_code)[ 0 ] == '2':
        deploy_version = json.loads( r.text )[ 'version' ]
        print( 'Current deployed version is ' + str(deploy_version) + '.\n' )

    elif str(r.status_code) == '404':
        print( 'Error: No blueprint with UUID ' + bp_uuid + ' found.\n' )
      
    else:
        print( 'Unspecified error.  Please check the Apstra logs for details.\n' )     

    return(deploy_version)

#
# Revert blueprint changes to the last deployed state
def revert_bp( token, url, bp_uuid ):
    success = False
    url = url + '/blueprints/' + bp_uuid + '/revert'
    req_headers = { 'AUTHTOKEN': token }

    print( 'Reverting staged blueprint back to last commit...\n' )
    r = req.post( url, headers=req_headers, verify=False )

    if str(r.status_code)[ 0 ] == '2':
        print( 'Completed revert of blueprint.\n' )
        success = True

    elif str(r.status_code) == '404':
        print( 'Error: No blueprint with UUID ' + bp_uuid + ' found.\n' )
   
    elif str(r.status_code) == '409':
        print( 'Error: Blueprint is in create state and can not be reverted.\n' )
   
    else:
        print( 'Unspecified error.  Please check the Apstra logs for details.\n' )     

    return( success )


###############################
# Operations on property sets #
###############################

#
# Get list of property sets from a blueprint as JSON
def get_ps_list( token, url, bp_uuid ):
    json_out = ''
    url = url + '/blueprints/' + bp_uuid + '/property-sets'
    req_headers = { 'AUTHTOKEN': token }
    r = req.get( url, headers=req_headers, verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Failed to get property set list for blueprint ' + bp_uuid + '.  Quitting.\n')
        quit()

    json_out = json.loads(r.text)
    print( 'Getting property set list from blueprint...\n' )

    return( json_out )

#
# Create a new property set in a freeform blueprint
def post_ps( token, url, bp_uuid, peer_prop_json, ps_label ):
    ps_id = ''
    url = url + '/blueprints/' + bp_uuid + '/property-sets'
    ps_payload = { 'label': ps_label, 'values': peer_prop_json }
    req_headers = { 'AUTHTOKEN': token }

    r = req.post( url, headers=req_headers, data = json.dumps( ps_payload ), verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Publish of property set failed, got HTTP ' + str(r.status_code) +
               ' error.  Quitting.\n' )
        quit()

    ps_id = json.loads(r.text)[ 'id' ]
    print( 'Published new property set with ID = ' + ps_id + '.\n' )
    
    return( ps_id )

#
# Replace an existing property set in a freeform blueprint
def patch_ps( token, url, bp_uuid, peer_prop_json, ps_id, ps_label ):
    url = url + '/blueprints/' + bp_uuid + '/property-sets/' + ps_id
    ps_payload = { 'label': ps_label, 'values': peer_prop_json }
    req_headers = { 'AUTHTOKEN': token }

    r = req.patch( url, headers=req_headers, data = json.dumps( ps_payload ), verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Update of property set ' + ps_label + ' failed, got HTTP ' +
                str(r.status_code) + ' error.  Quitting.\n' )
        quit()

    print( 'Updated property set ' + ps_label + '.\n' )
    
    return( r.status_code )

##############################
# Device (system) operations #
##############################

def get_dev_context( token, url, bp_id, sys_id ):
    dev_context = {}
    url = url + '/blueprints/' + bp_id + '/systems/' + sys_id + '/config-context'
    req_headers = { 'AUTHTOKEN': token }

    r = req.get( url, headers=req_headers, verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Couldn\'t fetch context for system ID ' + sys_id +
               '. Got HTTP ' + str(r.status_code) + ' error.  Quitting.\n' )
        quit()

    dev_context = json.loads(r.text)
    dev_context = json.loads( dev_context[ 'context' ] )

    return( dev_context )

#
# Get a list of systems in the target blueprint
def get_systems_in_bp( token, url, bp_id, ):
    sys_list = []
    req_headers = { 'AUTHTOKEN': token }
    url = url + '/blueprints/' + bp_id + '/systems'
    r = req.get( url, headers = req_headers, verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Error getting systems in ' + bp_id + '. Quitting.' )
        sys_list= []
        quit()

    json_out = json.loads(r.text)
    for item in json_out['items']:
        sys_list.append( item['system_id'] )

    return( sys_list )

