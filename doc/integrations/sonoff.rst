Sonoff
***************

`Sonoff <https://sonoff.tech/>`_ is a line of smart power control equipment,
which can be integrated with EVA ICS.

Setup
=====

.. note::

   EVA ICS can work only with Sonoff equipment running `Tasmota
   <https://github.com/arendst/Sonoff-Tasmota>`_ firmware.

All Sonoff equipment is controlled via 2 PHI modules:

* **sonoff_basic** all Sonoff single-port equipment
* **sonoff_mch** all Sonoff multi-port equipment

As Sonoff exchange data via MQTT only, you must setup :ref:`MQTT notifier
<mqtt_>` for :doc:`/uc//uc` first. Note that PHI modules always require full
MQTT topic despite notifier space is set.

For the initial integrations, we recommend simple MQTT server `mosquitto
<https://mosquitto.org>`_, which is included in all popular Linux distributions
and is very easy to configure.

Let's configure notifier if it doesn't exists yet. Consider we have MQTT server
setup on IP *192.168.100.1* with username *eva* and password *123*:

.. code:: shell

   eva ns uc create eva_1 mqtt:eva:123@192.168.100.1
   eva ns uc test eva_1
   eva ns uc enable eva_1
   # restart controller if everything is okay
   eva uc server restart

After MQTT server / notifier is set up, configure Sonoff connection to MQTT
server and set the control / monitoring topic, e.g. to *equipment/sonoff1*.
We'll use in this example notifier named *eva_1*, which is default notifier in
EVA ICS controllers. If you use different notifier ID, it should be specified
in *n* config param of PHI module.

Let's connect the single-port Sonoff to :doc:`/uc/uc`:

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/relays/sonoff_basic.py
   eva uc phi load sonoff1 sonoff_basic -c t=equipment/sonoff1 -y
   # create unit
   eva uc create unit:lights/lamp1 -y
   # assign driver
   # note: if sonoff_mch module is used, you must also specify "-c port=N"
   # param, where N is port number
   eva uc driver assign unit:lights/lamp1 sonoff1.default -y
   # enable unit actions
   eva uc action enable unit:lights/lamp1
