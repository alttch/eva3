Philips Hue
***********

EVA ICS can work with `Philips Hue <https://meethue.com>`_  via Hue bridge.

Setup
=====

Connect LEDs to Hue bridge.

.. note::

   In EVA ICS all LEDs have common single format, where unit status is 0 for
   OFF, 1 for ON and unit value is 24-bit hexadecimal color code.

   Philips Hue uses XYB palette which can not be properly converted back to
   hexadecimal RGB. For that reason, only unit status (0/1) is updated in case
   if Hue LED is additionally controlled by 3rd party or native Philips app.

Let's connect the bulb to :doc:`/uc/uc`:

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/lights/philips_hue_leds.py
   # PHI module for Philips Hue supports "discover" command, so we can discover
   # the bridge in network to obtain its IP
   eva uc phi discover philips_hue_leds
   # consider the bridge has IP address 192.168.1.100. To make a link between
   # PHI and Hue Bridge, you must either specify "user" configuration param or
   # press "link" button on Hue bridge and load PHI within 30 seconds.
   eva uc phi load hue1 philips_hue_leds -c host=192.168.1.100 -y
   # create unit
   eva uc create unit:lights/lamp1 -y
   # list available PHI ports
   eva uc phi ports hue1
   # assign driver, e.g. to port 1
   eva uc driver assign unit:lights/lamp1 hue1.default -c port=1 -y
   # enable unit actions
   eva uc action enable unit:lights/lamp1
   # turn the bulb on and set it to, e.g. red:
   eva uc action exec unit:lights/lamp1 1 -v "#FF0000" -w 5

.. note::

   PHI tries to delete specified (or created) user, when unloading.

