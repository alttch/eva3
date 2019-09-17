Denkovi
*******

`Denkovi Electronics <https://denkovi.com/>`_ is a hardware developer/vendor,
which is focused on relay modules and accessories.

Equipment supported
===================

* **dae_ip16r** smartDEN-IP-16R 16-port TCP/IP controlled relay
* **dae_pbro5ip** DAE-PB-RO5-DAEnetIP4 5-port TCP/IP controlled relay
* **dae_ro16_modbus** DAE-RO16-MODBUS 16-port Modbus relay
* **dae_ip32in** smartDEN IP-32IN (digital inputs only)

Setup
=====

Connect relay module to local network, make sure SNMP API is enabled.

Let's connect 16-port relay to :doc:`/uc/uc`. Consider relay module has IP
address 192.168.1.100, SNMP community is default (*private*):

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/relays/dae_ip16r.py
   eva uc phi load relay1 dae_ip16r -c host=192.168.1.100 -y
   # create units
   eva uc create unit:lights/lamp1 -y
   eva uc create unit:lights/lamp2 -y
   # assign driver. consider lamp1 is on port 1, lamp 2 on port 2
   eva uc driver assign unit:lights/lamp1 relay1.default -c port=1 -y
   eva uc driver assign unit:lights/lamp2 relay1.default -c port=2 -y

Performance tuning
==================

If PHI become slow, it's recommended to install **python3-netsnmp** module,
which is much faster than native SNMP implementation:

Put *python3-netsnmp* to *EXTRA* var in /opt/eva/etc/venv, then run

.. code:: shell

   /opt/eva/install/build-venv

You will also probably need *libsnmp-dev* system package. Check module setup
output for details.
