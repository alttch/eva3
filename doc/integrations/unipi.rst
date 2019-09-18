UniPi
*****

`UniPi <https://www.unipi.technology/>`_ is a hardware developer/vendor, which
is focused on industrial microcomputers.

Hardware recommendations
========================

To get max performance and avoid slowdowns, it's highly recommended to use at
least UHS-I Class SD Card or faster for UniPi Neuron series.

Installation
============

Local
-----

You may install EVA ICS directly on UniPi computers. As UniPi uses non-standard
Raspbian distribution, append *--force-os raspbian* to EVA ICS installer (run
all commands as root):

.. code:: shell

   curl geteva.cc | sudo sh /dev/stdin -a --force-os raspbian

It's also recommended to double-check is UTF-8 locale supported properly and if
no - reconfigure it with

.. code:: shell

   dpkg-reconfigure locales

Remote
------

:doc:`/uc/uc` talks with UniPi via :doc:`/modbus`. To let UniPi Modbus daemon
answer remote requests, add "--listen" option (file
*/etc/default/unipi-modbus-tools*):

.. code:: shell

  DAEMON_OPTS="--listen=0.0.0.0 -a 255"

then restart UniPi Modbus daemon:

.. code:: shell

   systemctl restart unipitcp.service

1-Wire
======

If installed locally, EVA ICS can use UniPi :doc:`1-Wire </owfs>` bus directly.

For Neuron series, owfs virtual bus for :doc:`/uc/uc` must be created as:

.. code:: shell

   eva uc owfs create local1 "i2c=/dev/i2c-1:ALL" -y

For Axon series:

.. code:: shell

   eva uc owfs create local1 "/dev/i2c-0 --w1" -y


Inputs/outputs
==============

EVA ICS has 4 pre-built PHI modules for UniPi (model Axon S115), which can be
also used as a templates for other UniPi models. As all models use very similar
Modbus register maps, PHIs are compatible or require only slight modifications.

* **unipi_axon_s115_ain** analog input
* **unipi_axon_s115_aout** analog output
* **unipi_axon_s115_din** digital inputs
* **unipi_axon_s115_dout** digital outputs

Consider, UniPi has IP address 192.168.1.100 and EVA ICS :doc:`/uc/uc` is
installed on remote host (for local installation use "localhost" or
"127.0.0.1" for Modbus virtual port configuration). If your UniPi has RS485
port, you may also connect device via RS485-1 (default).

.. code:: shell

   # create Modbus virtual port
   eva uc modbus create upi1 tcp:192.168.1.100:502 -y
   eva uc modbus test upi1

   # download PHIs
   eva uc phi download https://get.eva-ics.com/phi/unipi/axon/unipi_axon_s115_ain.py
   eva uc phi download https://get.eva-ics.com/phi/unipi/axon/unipi_axon_s115_aout.py
   eva uc phi download https://get.eva-ics.com/phi/unipi/axon/unipi_axon_s115_din.py
   eva uc phi download https://get.eva-ics.com/phi/unipi/axon/unipi_axon_s115_dout.py

   # load PHIs
   eva uc phi load upi1_ain unipi_axon_s115_ain -c port=upi1,unit=1 -y
   eva uc phi load upi1_aout unipi_axon_s115_aout -c port=upi1,unit=1 -y
   # DIN/DOUT PHIs can update states by themselves, let's update them every
   # second
   eva uc phi load upi1_din unipi_axon_s115_din -c port=upi1,unit=1,update=1 -y
   eva uc phi load upi1_dout unipi_axon_s115_dout -c port=upi1,unit=1,update=1 -y

   # let's create sensors for DIN2 and 3 and AIN
   eva uc create sensor:upi1/din2 -y
   eva uc create sensor:upi1/din3 -y
   eva uc create sensor:upi1/ain -y

   # assign drivers to sensors
   eva uc driver assign sensor:upi1/din2 upi1_din.default -c port=2 -y
   eva uc driver assign sensor:upi1/din3 upi1_din.default -c port=3 -y
   eva uc driver assign sensor:upi1/ain upi1_ain.default -y

   # PHI for AIN doesn't update the state, so set sensor to update it e.g.
   # every second:
   eva uc config set sensor:upi1/ain update_interval 1 -y

   # let's create units for DOUT2 and 3 and AOUT
   eva uc create unit:upi1/dout2 -y
   eva uc create unit:upi1/dout3 -y
   eva uc create unit:upi1/aout -y

   # enable unit actions
   eva uc action enable unit:upi1/dout2
   eva uc action enable unit:upi1/dout3
   eva uc action enable unit:upi1/aout

   # assign drivers to units
   eva uc driver assign unit:upi1/dout2 upi1_dout.default -c port=2 -y
   eva uc driver assign unit:upi1/dout3 upi1_dout.default -c port=3 -y
   eva uc driver assign unit:upi1/aout upi1_aout.default -y

   # let's set analog output to 3.3 volts
   eva uc action exec unit:upi1/aout 1 -v 3.3
