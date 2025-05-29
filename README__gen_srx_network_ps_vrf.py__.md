# Requirements for gen_srx_network_ps_vrf.py
To make this work, you must have the following...

## Reference design blueprint
Yes, you need a "RefDes" blueprint for your data center.  That design should
include either a single SRX or an SRX MNHA pair (these are just generic systems
in the RefDes blueprint) attached to the border/service leaf rack -- best to
have an ESI-LAG pair of border leaves in the rack design, and create an ESI-LAG
bundle to connect each SRX to both border leaves.

Assuming you have a border leaf pair...

- Apply the system tag `border1` to one of the border leaves, and apply the
  system tag `border2` to the other.

- Apply the system tag `fw_node1` to one of the firewalls, and apply the system
  tag `border2 to the other firewall.  You must also assign the correct BGP
  autonomous system numbers (ASN's) to the firewalls in the node properties
  form for each.

- Create your routing zones (a.k.a. VRF's).  For each VRF that needs to
  route traffic externally via the firewall, create a virtual network in the
  VRF that will peer with the firewalls via BGP.  Apply the tag `peer_to_fw`
  to each of those peering VN's.

- Create a connectivity template for BGP peering to each SRX in each VRF.
  For example, if you have VRF's named `BLUE` and `RED` and an MNHA pair of
  SRX firewalls, you need four CT's:  `BGP to FW1 in BLUE`,
  `BGP to FW2 in BLUE`, `BGP to FW1 in RED`, and `BGP to FW2 in RED`.  Use the
  pre-defined `BGP over L2 Connectivity` template and set the following:

  + `Virtual Network Tag Type` is `VLAN Tagged`

  + BGP `Peeer From` `Interface` and `Peer To` `Interface/Shared IP Endpoint`

- Once you've applied the CT's to the proper interfaces, navigate to Staged
  -> Virtual -> Floating IPs and set the firewall peer IP's as you prefer.

Once you have a complete and validated Staged config, you can commit the
changes.

### Freeform blueprint
You will build your SRX, or MNHA pair of SRX's, as a freeform blueprint.
The SRX (or SRX's) will be the only internal systems in this blueprint,
and this is where we will manage them.  You will add the border leaves from
the RefDes blueprint, and any other devices you might need knowledge of, as
external devices in this blueprint.  Build your blueprint such that each SRX
is connected to both border leaves via LAG bundle.  Connect the SRX's in
your MNHA pair to each other via LAG bundle as well.