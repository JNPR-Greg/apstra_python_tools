'''
gen_srx_prop_sets.py
    This script will grab details from an Apstra reference design blueprint
    and generate property sets for a freeform blueprint than configures
    the edge firewalls connected to that RefDes blueprint for BGP in each
    VRF defined in the RefDes blueprint.

    Last Updated:  2025-05-20 at 13:15
'''

import argparse as ap
import requests as req
import json
import getpass

# Add this to suppress the InsecureRequestWarning
from urllib3.exceptions import InsecureRequestWarning

from lib import apstra_utils as aosUtil

# Define some variables we'll use later
login_dict = { 'user': '', 'password': '', 'target': '', 'port': '' }
base_url = ''
token = ''
choice = ''

src_uuid = ''
src_sys_list = []
dst_uuid = ''

vn_json = ''
ps_id = ''
ps_label = ''

B1_TAG = 'border1'
B2_TAG = 'border2'
FW1_TAG = 'fw_node1'
FW2_TAG = 'fw_node2'
PEER_PROP_SET_NAME = 'peer_properties'
FW1_TAG_QUERY = "node('system', role='generic').in_('tag').node('tag', label='fw_node1')"
FW2_TAG_QUERY = "node('system', role='generic').in_('tag').node('tag', label='fw_node2')"

b1_context = { 'sys_tag': B1_TAG, 'sys_id': '', 'asn': '', 'fw1_if': '', 'fw2_if': '' }
b2_context = { 'sys_tag': B2_TAG, 'sys_id': '', 'asn': '', 'fw1_if': '', 'fw2_if': '' }
fw_vn_list = []
peer_prop_json = {}

cc_success = False

#########################
# Define some functions #
#########################

#
# Find VN's that service firewall connections
#
def get_fw_vn_list( json ):
    vn_list = []

    for vn_id, vn_data in json[ 'virtual_networks' ].items():
        if 'peer_to_fw' in vn_data[ 'tags' ]:
            vn_list.append( vn_id )

    return( vn_list )

#
# Build the vrf_dict_items for the peer_properties property set that we'll
# install in the SRX blueprint.  We'll assemble the property set elsewhere.
#
def build_proto_prop_set( token, url, bp_id, fw_vn_list, b1_context, b2_context ):
    sz_data = ''
    sz_id = ''
    vrf_dict_items = [ ]
    peer_prop_set = { }

    fw1_details = get_fw_details( token, url, bp_id, b1_context, FW1_TAG )
    fw2_details = get_fw_details( token, url, bp_id, b1_context, FW2_TAG )
    
    fw1_context = { 'sys_tag': FW1_TAG, 'node_id': fw1_details[ 'fw' ][ 'id' ],
                    'asn': fw1_details[ 'bgp' ][ 'domain_id' ] }
    fw2_context = { 'sys_tag': FW2_TAG, 'node_id': fw2_details[ 'fw' ][ 'id' ],
                    'asn': fw2_details[ 'bgp' ][ 'domain_id' ] }

    asn_dict = {
                    'asn': {
                        'leaf1': b1_context[ 'asn' ],
                        'leaf2': b2_context[ 'asn' ],
                        'fw_node1': fw1_context[ 'asn' ],
                        'fw_node2': fw2_context[ 'asn' ]
                    }
                }
    
    peer_prop_set.update( asn_dict )
    
    for vn in fw_vn_list:
        leaf1_ip4 = ''
        leaf2_ip4 = ''
        fw1_ip4 = ''
        fw2_ip4 = ''
        vn_data = aosUtil.get_vn_data( token, url, bp_id, vn )
        sz_id = vn_data[ 'security_zone_id' ]
        sz_data = aosUtil.get_sz_data( token, url, bp_id, sz_id )

        vrf_name = sz_data[ 'vrf_name' ]
        vlan_id = vn_data[ 'reserved_vlan_id' ]
        prefix_bits = vn_data[ 'ipv4_subnet' ].split('/')[ 1 ]

        for svi in vn_data[ 'svi_ips' ]:
            if svi[ 'system_id' ] == b1_context[ 'sys_id' ]:
                leaf1_ip4 = svi[ 'ipv4_addr' ].split( '/' )[ 0 ]

            if svi[ 'system_id' ] == b2_context[ 'sys_id' ]:
                leaf2_ip4 = svi[ 'ipv4_addr' ].split( '/' )[ 0 ]

        for float in vn_data[ 'floating_ips' ]:
            fw_ip4 = float[ 'ipv4_addr' ] .split( '/' )[ 0 ]
            fw_node_id = float[ 'generic_system_ids' ][ 0 ]

            if fw_node_id == fw1_context[ 'node_id' ]:
                fw1_ip4 = fw_ip4
                fw1_asn = fw1_context[ 'asn' ]

            if fw_node_id == fw2_context[ 'node_id' ]:
                fw2_ip4 = fw_ip4
                fw2_asn = fw2_context[ 'asn' ]

        vrf_dict_items.append( {'name': vrf_name,
                                'vlan_id': vlan_id,
                                'prefix_bits': prefix_bits,
                                'fw1_ip4': fw1_ip4,
                                'fw2_ip4': fw2_ip4,
                                'leaf1_ip4': leaf1_ip4,
                                'leaf2_ip4': leaf2_ip4 }
                             )
        
    vrf_dict = { 'vrfs': vrf_dict_items }
    peer_prop_set.update(vrf_dict )

    return( peer_prop_set )

#
# Check generic system for specific tags
#
def match_tag_to_node( token, url, bp_id, node_id ):
    sys_context = ''
    url = url + '/blueprints/' + bp_id + '/qe'
    req_headers = { 'AUTHTOKEN': token }
    qe_string1 = 'node(\'system\', name=\'systems\', role=\'generic\', id=\'' + node_id + '\')' + \
                 '.in_().node(\'domain\', name=\'asn\')' + \
                 '.out().node(\'system\')' + \
                 '.in_().node(\'tag\', name=\'tags\', label=\'' + FW1_TAG + '\')'
    qe_string2 = 'node(\'system\', name=\'systems\', role=\'generic\', id=\'' + node_id + '\')' + \
                 '.in_().node(\'domain\', name=\'asn\')' + \
                 '.out().node(\'system\')' + \
                 '.in_().node(\'tag\', name=\'tags\', label=\'' + FW2_TAG + '\')'
    qe_payload1 = { 'query': qe_string1 }
    qe_payload2 = { 'query': qe_string2 }

    r = req.post( url, headers=req_headers, data = json.dumps(qe_payload1), verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Graph query failed, got HTTP ' + str(r.status_code) +
               ' error.  Quitting.\n' )
        quit()

    if json.loads(r.text)[ 'count' ] == 1:
        sys_context = json.loads(r.text)[ 'items' ][ 0 ]
    
    r = req.post( url, headers=req_headers, data = json.dumps(qe_payload2), verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Graph query failed, got HTTP ' + str(r.status_code) +
               ' error.  Quitting.\n' )
        quit()

    if json.loads(r.text)[ 'count' ] == 1:
        sys_context = json.loads(r.text)[ 'items' ][ 0 ]
    
    return( sys_context )

#
# Get config context for FW node1
#
def get_fw_details( token, url, bp_id, border_context, fw_tag ):
    fw_context = ''
    fw_if = ''
    b_tag = border_context[ 'sys_tag' ]
    if fw_tag == FW1_TAG:
        fw_if = border_context[ 'fw1_if' ]

    if fw_tag == FW2_TAG:
        fw_if = border_context[ 'fw2_if' ]

    url = url + '/blueprints/' + bp_id + '/qe'
    req_headers = { 'AUTHTOKEN': token }
    qe_string = 'node(\'system\', tag=has_any([\'' + b_tag + '\']))' + \
                 '.out(\'hosted_interfaces\')' + \
                 '.node(\'interface\', if_name=\'' + fw_if + '\')' + \
                 '.out(\'link\').node(\'link\')' + \
                 '.in_(\'link\').node(\'interface\')' + \
                 '.in_(\'hosted_interfaces\')' + \
                 '.node(\'system\', name=\'fw\', tag=has_any([\'' + fw_tag + '\']))' + \
                 '.in_().node(\'domain\', name=\'bgp\')'
    qe_payload = { 'query': qe_string }

    r = req.post( url, headers=req_headers, data = json.dumps(qe_payload), verify=False )

    if str(r.status_code)[ 0 ] != '2':
        print( 'Graph query failed, got HTTP ' + str(r.status_code) +
               ' error.  Quitting.\n' )
        quit()

    fw_context = json.loads(r.text)[ 'items' ][ 0 ]    

    return ( fw_context )


###################################
#                                 #
# Now for real - main starts here #
#                                 #
###################################

req.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
print( '\n\n' )

#
# Let's login to the Apstra instance
#
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

#
# We need a reference fabric as the source and a freeform fabric as the
# destination for our operations here.
#
while src_uuid == '':
    src_uuid = input( 'Enter UUID of source (reference) blueprint: ' )
    src_data = aosUtil.get_bp_data( token, base_url, src_uuid )

    if src_data[ 'design' ] == 'freeform':
        print( 'Error.  Source blueprint must be a reference design.\n')
        src_uuid = ''

while dst_uuid == '':
    dst_uuid = input( 'Enter UUID of SRX (freeform) blueprint: ' )
    dst_data = aosUtil.get_bp_data( token, base_url, dst_uuid )

    if dst_data[ 'design' ] != 'freeform':
        print( 'Error.  Destination blueprint must be a freeform design.\n')
        dst_uuid = ''


vn_json = aosUtil.get_vn_list( token, base_url, src_uuid )
fw_vn_list = get_fw_vn_list( vn_json )

#
# Get the context for systems in the source BP and find the ID's of the
# systems tagged as 'border1' and 'border2'
#
print( 'Searching for leaves tagged ' + B1_TAG + ' & ' + B2_TAG +
       ' in source blueprint...\n' )
src_sys_list = aosUtil.get_systems_in_bp( token, base_url, src_uuid )
for sys in src_sys_list:
    sys_context = aosUtil.get_dev_context( token, base_url, src_uuid, sys )

    if B1_TAG in sys_context[ 'system_tags' ]:
        b1_context[ 'sys_id' ] = sys_context[ 'node_id' ]
        b1_context[ 'asn' ] = sys_context[ 'bgpService' ][ 'asn' ]

        for if_name, if_data in sys_context[ 'interface' ].items():
            if FW1_TAG in if_data[ 'tags' ]:
                b1_context[ 'fw1_if' ] = if_data[ 'intfName' ]

            if FW2_TAG in if_data[ 'tags' ]:
                b1_context[ 'fw2_if' ] = if_data[ 'intfName' ]
                

    if B2_TAG in sys_context[ 'system_tags' ]:
        b2_context[ 'sys_id' ] = sys_context[ 'node_id' ]
        b2_context[ 'asn' ] = sys_context[ 'bgpService' ][ 'asn' ]

        for if_name, if_data in sys_context[ 'interface' ].items():
            if FW1_TAG in if_data[ 'tags' ]:
                b2_context[ 'fw1_if' ] = if_data[ 'intfName' ]

            if FW2_TAG in if_data[ 'tags' ]:
                b2_context[ 'fw2_if' ] = if_data[ 'intfName' ]
                
#
# Build the vrf_dict_items we need in the destination BP so that the SRX's
# can peer with the border leaves in each VRF.  Once we have that, the
# peer_properties property set is just a concatenation of the asn_dict_items
# and the vrf_dict_items.
#
peer_prop_set = build_proto_prop_set( token, base_url, src_uuid, fw_vn_list, b1_context, b2_context )

#
# Now we can install the peer_properties property set in the destination BP.
# POST if the property set doesn't already exist.  PATCH if it does.
#
ps_list = aosUtil.get_ps_list( token, base_url, dst_uuid )

for ps in ps_list[ 'items' ]:
    if ps[ 'label' ] == PEER_PROP_SET_NAME:
        ps_id = ps[ 'property_set_id' ]

if ps_id == '' :
    aosUtil.post_ps( token, base_url, dst_uuid, peer_prop_set, PEER_PROP_SET_NAME )

else:
    aosUtil.patch_ps( token, base_url, dst_uuid, peer_prop_set, ps_id, PEER_PROP_SET_NAME )

#
# Let's run a commit-check on the SRX blueprint.
# If it looks good, then we can commit.
#
cc_success = aosUtil.commit_check( token, base_url, dst_uuid )
while not cc_success:
    choice = ''
    print( 'How would you like to proceed?' )
    print( '  [ 1 ] Re-run the commit-check operation' )
    print( '  [ 2 ] Revert staged changes back to the current deployed blueprint\n' )
    print( '  Any other entry will do nothing and just quit.\n' )

    while choice == '':
        input( 'Choice: ' )
    
    if str.choice == '1':
        cc_success = aosUtil.commit_check( token, base_url, dst_uuid )

    elif str.choice == '2':
        choice = ''
        aosUtil.revert_bp( token, base_url, dst_uuid )

    else:
        quit()

if cc_success:
    choice = ''
    while choice == '':
        choice = input( 'Would you like to commit changes to the SRX blueprint? [y|n]:  ')

    if choice == 'y' or choice == 'Y':
        aosUtil.deploy_bp( token, base_url, dst_uuid )

#
# Time to declare victory and logout!
# 
aosUtil.logout( token, base_url )

quit()
