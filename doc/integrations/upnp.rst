UPnP
****

EVA ICS controllers
===================

Starting from version 3.2.6, controllers can find each other in local network
via UPnP and automatically connect peer-to-peer without MQTT server.

To perform this, controllers send SSDP broadcast requests to non-standard SSDP
UDP port *1912* for :doc:`/uc/uc` and *1917* for :doc:`/lm/lm`. Requests are
performed on controller start and then repeated with 2-minute interval.

Notes:

* To let controller be discovered by other, *listen* option must be configured
  in *[upnp]* section of controller configuration file (starting from 3.2.6 -
  enabled by default).

* To let controller (LM PLC or :doc:`SFA</sfa/sfa>`) discover others,
  *discover_on* option must be set in *[upnp]* section of controller
  configuration file either to "\*" (scan all interfaces) or to the list of
  network interfaces (comma separated).

* To let controller connect to the discovered one, both must have equal
  *default* API key. API key *hosts_allow* permission should include the proper
  IP addresses or networks.

* Discovered controllers are marked as *dynamic*, their configuration is not
  saved (until marked as *static* or controller *masterkey* is set in SFA,
  when *cloud_manager* mode is enabled).

* If controllers have static IP addresses (or static leases, assigned by DHCP
  server), it's highly recommended to mark them as *static* as soon as they
  were discovered.

3rd-party equipment
===================

Some of EVA ICS :doc:`PHI modules</drivers>` support "discover" command, which
allows to automatically find `UPnP
<https://en.wikipedia.org/wiki/Universal_Plug_and_Play>`_-enabled equipment in
local network via `SSDP
<https://en.wikipedia.org/wiki/Simple_Service_Discovery_Protocol>`_ protocol.

Built-in SSDP function **discover**, located in *eva.uc.drivers.tools.ssdp*
module can be used in custom PHI modules as well. Refer to
:doc:`/phi_development` for more info.
