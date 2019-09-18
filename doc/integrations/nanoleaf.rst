Nanoleaf
********

`Nanoleaf <https://nanoleaf.me/>`_  is a beautiful mosaic LED system, which can
be connected to EVA ICS via its local API.

Setup
=====

Make sure Nanoleaf is connected to the network.

.. note::

   In EVA ICS all LEDs have common single format, where unit status is 0 for
   OFF, 1 for ON and unit value is 24-bit hexadecimal color code.

   Nanoleaf PHI also supports color profiles, you may set them with unit value.
   Additionally, profile brighness can be specified after comma, e.g.
   "Snowfall,50"

Let's connect Nanoleaf to :doc:`/uc/uc`:

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/lights/nanoleaf.py
   # PHI module for Nanoleaf supports "discover" command, so we can discover
   # the equipment in network to obtain its IP
   eva uc phi discover nanoleaf
   # consider Nanoleaf has IP address 192.168.1.100. To make a link between
   # PHI and equipment, you must either specify authentication token with
   # "token" config param or press power button for 7 seconds before loading
   # PHI module
   eva uc phi load nano1 nanoleaf -c host=192.168.1.100 -y
   # create unit
   eva uc create unit:lights/nl1 -y
   # assign driver
   eva uc driver assign unit:lights/nl1 nano1.default -y
   # turn Nanoleaf on and set it to, e.g. red:
   eva uc action exec unit:lights/nl1 1 -v "#FF0000" -w 5
   # enable unit actions
   eva uc action enable unit:lights/n1
   # change Nanoleaf color profile to Snowfall with 50% brighness.
   eva uc action exec unit:lights/nl1 1 -v "Snowfall,50" -w 5

.. note::

   PHI tries to delete specified (or created) token, when unloading.

