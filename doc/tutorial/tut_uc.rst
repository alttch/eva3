Universal Controller configuration
**********************************

* EVA Tutorial parts

  * :doc:`Intro<tutorial>`
  * **Universal Controller configuration** << we are here
  * :doc:`tut_lm`
  * :doc:`tut_sfa`
  * :doc:`tut_ui`

So, let us proceed with our configuration. Connect the equipment to
:doc:`/uc/uc` and configure the :doc:`notification system</notifiers>`.

.. contents::

Connecting ventilation
======================

create two :ref:`units<unit>` for ventilation:

.. code-block:: bash

    uc-cmd create unit:ventilation/vi -y # internal
    uc-cmd create unit:ventilation/ve -y # external

Method 1: with scripts
----------------------

As a first step, create the variable for controlling SR-201 in order not to
write the full relay control commands anew:

.. code-block:: bash
    
    uc-cmd cvar set REL1_CMD "SR-201 192.168.22.3"

As far as both ventilation systems are connected via the same relay, and it
displays the states of all ports at once, let's create a multiupdate for
updating their status with a single command:

.. code-block:: bash

    uc-cmd create mu:ventilation/mu1 -y
    uc-cmd config set mu:ventilation/mu1 items unit:ventilation/vi,unit:ventilation/ve

and the :doc:`script</item_scripts>` for this multiupdate named
**xc/uc/mu1_update**:

.. code-block:: bash

    #!/bin/sh

    ${REL1_CMD} | head -2

.. note::

    After creating a script file, don't forget to set its executable
    permissions (*chmod +x scriptfile*)

Let's check the script:

.. code-block:: bash

    test-uc-xc xc/uc/mu1_update

.. code-block:: text

    Reading custom vars from /opt/eva/runtime/uc_cvars.json

    REL1_CMD = "SR-201 192.168.22.3"
    
    Starting 'xc/uc/mu1_update'
    
    stime: 1507923323.396813
    etime: 1507923323.400836
    duration: 0.004023 sec  ( 4.022598 msec )
    exitcode: 0
    
    ---- STDOUT ----
    0
    0

    ---- STDERR ----
    ----------------

Then we need to create two scripts for the relay control.

For internal ventilation, named **xc/uc/vi**

.. code-block:: bash

    #!/bin/sh

    ${REL1_CMD} 1 $2

and for external ventilation, named **xc/uc/ve**

.. code-block:: bash

    #!/bin/sh

    ${REL1_CMD} 2 $2

Enable the ventilation control:

.. code-block:: bash

    uc-cmd action enable unit:ventilation/vi
    uc-cmd action enable unit:ventilation/ve

set a multiupdate to update unit states every 30 seconds

.. code-block:: bash

    uc-cmd config set mu:ventilation/mu1 update_interval 30 -y

Method 2: with driver
---------------------

Starting from EVA 3.1 you can use pre-made :doc:`drivers</drivers>`. Let's do
the above with driver.

Download PHI module:

.. code-block:: bash

    uc-cmd phi download https://get.eva-ics.com/phi/relays/sr201.py

Load PHI module to controller. As **sr201** PHI provides **aao_get** feature,
set *update=30* to update all items which use drivers with this PHI every 30
seconds:

.. code-block:: bash

    uc-cmd phi load relay1 sr201 -c host=192.168.22.3,update=30 -y

Let's test it:

.. code-block:: bash

    uc-cmd phi test relay1 self

After loading **sr201** PHI automatically created driver "relay1.default" with
"basic" LPI. As we have a simple logic, let's use it as-is. Set driver to both
ventilation units:

.. code-block:: bash

    uc-cmd driver set unit:ventilation/vi relay1.default -c port=1 -y
    uc-cmd driver set unit:ventilation/ve relay1.default -c port=2 -y


Connecting a temperature sensor
===============================

Create sensor in UC:

.. code-block:: bash

    uc-cmd create sensor:env/temp1

(Consider Linux **w1-gpio** and **w1-therm** kernel modules are already loaded)

Let's find our sensor on a 1-Wire bus:

.. code-block:: bash

    ./xbin/w1_ls
    28-000006ef85d7

Method 1: with scripts
----------------------

Here it is. Create a script named **xc/uc/temp1_update**

.. code-block:: bash

    #!/bin/sh
 
    VALUE=`w1_therm 28-000006ef85d7` && echo 1 ${VALUE} || echo -1

Let the temperature update every 20 seconds:

.. code-block:: bash

    uc-cmd config set sensor:env/temp1 update_interval 20 -y

Method 2: with driver
---------------------

Download PHI module:

.. code-block:: bash

    uc-cmd phi download https://get.eva-ics.com/phi/sensors/env/w1_ds18n20.py

Load PHI module to controller. This is **universal** PHI which means you don't
need to specify particular sensor address when loading, it should be specified
later when you set driver to sensor:

.. code-block:: bash

    uc-cmd phi load w1t w1_ds18n20 -y

After loading w1_ds18n20 PHI automatically created driver "w1t.default" with
"sensor" LPI. As we have a simple logic, let's use it as-is. Set driver to
sensor:

.. code-block:: bash

    uc-cmd driver set sensor:env/temp1 w1t.default -c port=28-000006ef85d7 -y

As this PHI doesn't provide **aao_get** feature and we can't ask it to update
sensors automatically, set **update_interval** sensor property to let it
passively update itself every 20 seconds:

.. code-block:: bash

    uc-cmd config set sensor:env/temp1 update_interval 20 -y

Connecting a motion sensor
==========================

Create a sensor in UC:

.. code-block:: bash

    uc-cmd create sensor:security/motion1 -y

and configure the sensors controller to send :doc:`/snmp_traps` to our server
IP.

Method 1: with SNMP trap parser
-------------------------------

Switch on the debugging mode and look into the log file:

.. code-block:: bash

    uc-cmd debug on
    tail -f log/uc.log|grep "snmp trap data"

Let someone walk near the sensor and we'll catch SNMP trap data:

.. code-block:: text

    2017-10-13 18:52:42,568 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.2.1.1.3.0 = 549411751
    2017-10-13 18:52:42,569 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.6.3.1.1.4.1.0 = 1.3.6.1.4.1.3854.1.0.301
    2017-10-13 18:52:42,571 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.6.3.18.1.3.0 = 192.168.22.95
    2017-10-13 18:52:42,572 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.6.3.18.1.4.0 = 
    2017-10-13 18:52:42,574 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.6.3.1.1.4.3.0 = 1.3.6.1.4.1.3854.1
    2017-10-13 18:52:42,576 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.1.0 = 4
    2017-10-13 18:52:42,579 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.2.0 = 1
    2017-10-13 18:52:42,581 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.3.0 = 0
    2017-10-13 18:52:42,583 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.4.0 = 0
    2017-10-13 18:52:42,584 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.5.0 = Motion1
    2017-10-13 18:52:42,586 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.6.0 = MD Hall
    2017-10-13 18:52:44,583 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.2.1.1.3.0 = 549411951
    2017-10-13 18:52:44,584 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.6.3.1.1.4.1.0 = 1.3.6.1.4.1.3854.1.0.301
    2017-10-13 18:52:44,586 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.6.3.18.1.3.0 = 192.168.22.95
    2017-10-13 18:52:44,588 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.6.3.18.1.4.0 = 
    2017-10-13 18:52:44,589 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.6.3.1.1.4.3.0 = 1.3.6.1.4.1.3854.1
    2017-10-13 18:52:44,591 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.1.0 = 2
    2017-10-13 18:52:44,594 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.2.0 = 0
    2017-10-13 18:52:44,596 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.3.0 = 0
    2017-10-13 18:52:44,597 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.4.0 = 0
    2017-10-13 18:52:44,598 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.5.0 = Motion1
    2017-10-13 18:52:44,602 plant1  DEBUG uc traphandler_t_dispatcher: snmp trap data 1.3.6.1.4.1.3854.1.7.6.0 = MD Hall

As we can see, the sensor sends SNMP OID *1.3.6.1.4.1.3854.1.7.1.0 = 4* when
there is some activity and *1.3.6.1.4.1.3854.1.7.1.0 = 2* when the activity is
finished. If we disconnect the sensor from the sensorProbe, trap with the same
OID and value *7* will be received.

switch off the debugging mode

.. code-block:: bash

    uc-cmd debug off

append one ident var to let it parse only "its own" traps:

.. code-block:: bash

    uc-cmd config set sensor:security/motion1 snmp_trap.ident_vars "1.3.6.1.4.1.3854.1.7.6.0=MD Hall" -y

and use SNMP OID *1.3.6.1.4.1.3854.1.7.1.0* to monitor it:

.. code-block:: bash

    uc-cmd config set sensor:security/motion1 snmp_trap.set_down 1.3.6.1.4.1.3854.1.7.1.0=7 -y
    uc-cmd config set sensor:security/motion1 snmp_trap.set_if 1,1:1.3.6.1.4.1.3854.1.7.1.0=4 -y
    uc-cmd config set sensor:security/motion1 snmp_trap.set_if 1,0:1.3.6.1.4.1.3854.1.7.1.0=2 -y

The final sensor configuration will look like:

.. code-block:: bash

    uc-cmd config get sensor:security/motion1

.. code-block:: json

    {
       "description": "",
       "expires": 0,
       "mqtt_update": null,
       "snmp_trap": {
           "ident_vars": {
               "1.3.6.1.4.1.3854.1.7.6.0": "MD Hall"
           },
           "set_down": {
               "1.3.6.1.4.1.3854.1.7.1.0": "7"
           },
           "set_if": [
               {
                   "status": 1,
                   "value": "1",
                   "vars": {
                       "1.3.6.1.4.1.3854.1.7.1.0": "4"
                   }
               },
               {
                   "status": 1,
                   "value": "0",
                   "vars": {
                       "1.3.6.1.4.1.3854.1.7.1.0": "2"
                   }
               }
           ]
       },
       "update_exec": null,
       "update_interval": 0,
       "update_timeout": null,
       "virtual": false
    }

The sensor is ready. It doesn't require any passive update script since its
state is updated with SNMP traps by the equipment.

Method 2: with driver
---------------------

Download PHI module:

.. code-block:: bash

    uc-cmd phi download https://get.eva-ics.com/phi/sensors/alarm/akcp_md.py

Load PHI module to controller. Consider motion sensor is connected to AKCP
sensor controller port #1 and it has IP address *192.168.22.5*. 

.. code-block:: bash

    uc-cmd phi load md1 akcp_md -c host=192.168.22.5,sp=1 -y

If one port is specified, **akcp_md** creates a driver with **ssp** LPI, which
doesn't need any additional options. Just set it to our sensor:

.. code-block:: bash

    uc-cmd driver set sensor:security/motion1 md1.default -y

The sensor is ready. It doesn't require any passive updates since its state is
updated with SNMP traps parsed by driver.

Connecting a hall light
=======================

Create hall light unit:

.. code-block:: bash

    uc-cmd create unit:light/lamp1 -y
    uc-cmd action enable unit:light/lamp1

Let it turn off automatically after 10 mins of inactivity:

.. code-block:: bash

    uc-cmd config set unit:light/lamp1 auto_off 600 -y

and enable the actions to be always executed:

.. code-block:: bash

    uc-cmd config set unit:light/lamp1 action_always_exec 1 -y

Method 1: with scripts
----------------------

So, now we have to connect the lamp to Denkovi IP-16R relay. Connect it
similarly to ventilation:

.. code-block:: bash

    uc-cmd cvar set REL2_CMD "snmpset -v2c -c private 192.168.22.4 .1.3.6.1.4.1.42505.6.2.3.1.3"
    uc-cmd cvar set REL2_UPDATE_CMD "snmpget -v2c -c public 192.168.22.4 .1.3.6.1.4.1.42505.6.2.3.1.3"

This relay returns the status of each port separately. Additionally, there is
only one connected device and, therefore, we won't create a multiupdate for the
unit and let it update the state with its own update script.

Create a script named **xc/uc/lamp1_update**

.. code-block:: bash

    #!/bin/sh

    ${REL1_UPDATE_CMD}.1 | cut -d: -f2 | awk '{ print $1 }'

and the action script **xc/uc/lamp1**

.. code-block:: bash

    #!/bin/sh

    ${RELAY1_CMD}.1 i $2

Let's update the lamp state every 30 seconds:

.. code-block:: bash

    uc-cmd config set unit:light/lamp1 update_interval 30 -y

Method 2: with driver
---------------------

Download PHI module:

.. code-block:: bash

    uc-cmd phi download https://get.eva-ics.com/phi/relays/dae_ip16r.py

Load PHI module to controller. This is **universal** PHI which means you don't
need to specify particular relay host when loading, it may be specified later
when you set driver to sensor. But in our example we have only one relay of
such type, so let's specify all options in PHI config: 

.. code-block:: bash

    uc-cmd phi load relay2 dae_ip16r -c host=192.168.22.4,retries=2

After loading **dae_ip16r** PHI automatically created driver "relay2.default"
with "basic" LPI. As we have a simple logic, let's use it as-is. Set driver to
lamp unit:

.. code-block:: bash

    uc-cmd driver set unit:light/lamp1 relay2.default -c port=2 -y

Let's update the lamp state every 30 seconds:

.. code-block:: bash

    uc-cmd config set unit:light/lamp1 update_interval 30 -y

Now open :doc:`/uc/uc_ei`, check the setup, switch on/off the units, see how the
sensor values are updated.

API keys configuration
======================

.. include:: skip_easy.rst

Connect :doc:`/lm/lm` and :doc:`/sfa/sfa` to this controller. Create two
:ref:`API keys<uc_apikey>` for them in *etc/uc_apikeys.ini*:

.. code-block:: ini

    [lm]
    key = secret_for_lm
    groups = #
    sysfunc = no
    hosts_allow = 127.0.0.1
     
    [sfa]
    key = secret_for_sfa
    groups = #
    sysfunc = no
    hosts_allow = 127.0.0.1

After adding the new keys, you need to restart UC, which we'll do later.
Firstly, you should connect it to :ref:`MQTT<mqtt_>`.

Notification system configuration
=================================

.. include:: skip_easy.rst

To let the item states be transferred from UC to other controllers in real
time, configure its notification system. Connect the server to the local
:ref:`MQTT<mqtt_>`:

.. code-block:: bash

    uc-notifier create eva_1 mqtt:eva:secret@localhost -s plaint1 -y
    uc-notifier subscribe state eva_1 -v '#' -g '#'

    uc-notifier config eva_1

.. code-block:: json

    {
        "enabled": true,
        "events": [
            {
                "groups": [
                    "#"
                ],
                "subject": "state",
                "types": [
                    "#"
                ]
            }
        ],
        "host": "localhost",
        "id": "eva_1",
        "password": "secret",
        "space": "plant1",
        "type": "mqtt",
        "username": "eva"
    }

Looks good. Now restart UC:

.. code-block:: bash

    ./sbin/uc-control restart

The configuration of :doc:`/uc/uc` is complete. Let's proceed to :doc:`tut_lm`.
