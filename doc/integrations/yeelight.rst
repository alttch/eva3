Xiaomi Yeelight
***************

`Yeelight <https://www.yeelight.com/>`_ is an affordable LED bulb with remote
control via WiFi, which can be integrated with EVA ICS.

Setup
=====

Firstly, bulb LAN control must be turned on (see
https://www.yeelight.com/en_US/developer for more info).

After, corresponding EVA ICS PHI module can be loaded and assigned to unit.

.. note::

   In EVA ICS all LEDs have common single format, where unit status is 0 for
   OFF, 1 for ON and unit value is 24-bit hexadecimal color code.

   Yeelight works in 2 modes: default (yellow-white) and color. If white color
   tone hex code is set to unit value, PHI module uses bulb API methods to put
   it in default mode and control brightness/temperature only, otherwise color
   mode is set and color LEDs are used.

Let's connect the bulb to :doc:`/uc/uc`:

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/lights/yeelight.py
   # PHI module for Yeelight supports "discover" command, so we can discover
   # the bulb in network to obtain its IP
   eva uc phi discover yeelight
   # consider the bulb has IP address 192.168.1.100
   eva uc phi load ye1 yeelight -c host=192.168.1.100 -y
   # create unit
   eva uc create unit:lights/lamp1 -y
   # assign driver
   eva uc driver assign unit:lights/lamp1 ye1.default -y
   # turn the bulb on and set it to, e.g. red:
   eva uc action exec unit:lights/lamp1 -s1 -v "#FF0000" -w 5

PHI module has additional configuration param *smooth=T*, where T is time in
milliseconds.
