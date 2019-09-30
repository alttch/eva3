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

Relay setup
===========

Connect relay module to local network, make sure SNMP API is enabled.

Let's connect smartDEN-IP-16R 16-port relay to :doc:`/uc/uc`. Consider relay
module has IP address 192.168.1.100, SNMP community is default (*private*):

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/relays/dae_ip16r.py
   eva uc phi load relay1 dae_ip16r -c host=192.168.1.100 -y
   # create units
   eva uc create unit:lights/lamp1 -y
   eva uc create unit:lights/lamp2 -y
   # assign driver. consider lamp1 is on port 1, lamp 2 on port 2
   eva uc driver assign unit:lights/lamp1 relay1.default -c port=1 -y
   eva uc driver assign unit:lights/lamp2 relay1.default -c port=2 -y
   # enable unit actions
   eva uc action enable unit:lights/lamp1
   eva uc action enable unit:lights/lamp2


smartDEN IP-32IN setup
======================

Connect module to local network, make sure SNMP API is enabled. To let
:doc:`/uc/uc` receive SNMP traps from digital inputs, open module web admin ->
*Digital Inputs* and select the ports you want to receive traps from. Make sure
trap value is 2 (both). Then enter *SNMP traps* section and enter :doc:`/uc/uc`
IP address and SNMP trap community (default is *eva*).

PHI ports are *1-16* for digital inputs, *a1-a8* for analog inputs and *t1-t8*
for temperature sensor (B57500M) inputs.

Consider we want to monitor digital input 2, analog input 3 and temperature
sensor input 4. Module IP address is 192.168.1.100, SNMP read community is
default (*public*):

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/sensors/misc/dae_ip32in.py
   eva uc phi load ip32in dae_ip32in -c host=192.168.1.100 -y
   # create sensors
   eva uc create sensor:inputs/din2 -y
   eva uc create sensor:inputs/ain3 -y
   eva uc create sensor:env/temp4 -y
   # enable sensors
   eva uc update sensor:inputs/din2 -s1
   eva uc update sensor:inputs/ain3 -s1
   eva uc update sensor:env/temp4 -s1
   # assign driver
   eva uc driver assign sensor:inputs/din2 ip32in.default -c port=2 -y
   eva uc driver assign sensor:inputs/ain3 ip32in.default -c port=a3 -y
   eva uc driver assign sensor:env/temp4 ip32in.default -c port=t4 -y
   # Consider, when DIN2 is modified, SNMP trap is being sent to UC, but let's
   # update sensor every 10 seconds anyway, in case if trap is lost:
   eva uc config set sensor:inputs/din2 update_interval 10 -y
   # analog input sensor will be updated every 500ms
   eva uc config set sensor:inputs/ain3 update_interval 0.5 -y
   # temperature sensor will be updated every 30 seconds
   eva uc config set sensor:env/temp4 update_interval 30 -y

.. note::

   Module returns value "- - -" if temperature sensor is not connected, but PHI
   module will set sensor status to *-1* (error).

Performance tuning
==================

If PHIs become slow, it's recommended to install **python3-netsnmp** module,
which is much faster than native SNMP implementation:

Put *python3-netsnmp* to *EXTRA* var in /opt/eva/etc/venv, then run

.. code:: shell

   /opt/eva/install/build-venv

You will also probably need *libsnmp-dev* system package. Check module setup
output for details.
