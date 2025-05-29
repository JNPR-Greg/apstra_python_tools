# apstra_python_tools
This is a collection of simple python tools that interact with Apstra via the
REST interface

- gen_srx_network_ps_type5.py -- Auto-generates a property set for an Apstra
  Freeform blueprint that contains a pair of SRX firewalls, possibly running
  in MNHA mode.  This lets us align the networking in a Reference Design
  blueprint (e.g., a "normal" Apstra date center blueprint) with the config
  of an SRX pair modeled in the Freeform BP.  This version of the script is
  intended for SRX as an East-West firewall that peers with the fabric via
  BGP peering where we exhange EVPN type-5 routes between the fabric and
  the firewalls.

- gen_srx_network_ps_vrf.py -- Same idea as above, but here the SRX peers with
  the fabric via BGP in each interesting VRF.  So here we're just exchanging
  "family inet" routes from each VRF.

- set_timers.py -- Handy for demos, the default behavior of this script will
  reduce the time it takes for anomalies to show up on the Dashboard.  There's
  a small dictionary in the file that defines the services we're interested in,
  and sets the timer values.  DO NOT use for production!

