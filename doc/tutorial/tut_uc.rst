Universal Controller configuration
==================================

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
----------------------

As a first step, create the variable for controlling SR-201 in order not to
write the full relay control commands anew:

.. code-block:: bash
    
    uc-cmd set_cvar -i REL1_CMD -v "SR-201 192.168.22.3"

create two :ref:`units<unit>` for the ventilation:

.. code-block:: bash

    uc-cmd create_unit -i vi -g ventilation -y # internal
    uc-cmd create_unit -i ve -g ventilation -y # external

As far as both ventilation systems are connected via the same relay, and it
display the states of all ports at once, let's create a multiupdate for
updating their status with a single command:

.. code-block:: bash

    uc-cmd create_mu -i mu1 -g ventilation -y
    uc-cmd set_prop -i mu1 -p items -v vi,ve

and the :doc:`script</item_scripts>` for this multiupdate named
**xc/uc/mu1_update**:

.. code-block:: bash

    #!/bin/sh

    ${REL1_CMD} | head -2

.. note::

    After you've created a script file, don't forget to set it executable
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

Then we need to create two scritps for the relay control.

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

    uc-cmd enable_actions -i vi
    uc-cmd enable_actions -i ve

set a multiupdate to update unit states every 30 seconds

.. code-block:: bash

    uc-cmd set_prop -i mu1 -p update_interval -v 30 -y

Connecting a temperature sensor
-------------------------------

(Consider Linux **w1-gpio** and **w1-therm** kernel modules are already loaded)

.. code-block:: bash

    uc-cmd create_sensor -i temp1 -g env

Let's find or sensor on a 1-Wire bus:

.. code-block:: bash

    ./xbin/w1_ls
    28-000006ef85d7

Here it is. Create a script named **xc/uc/temp1_update**

.. code-block:: bash

    #!/bin/sh
 
    VALUE=`w1_therm 28-000006ef85d7` && echo 1 ${VALUE} || echo -1

let the temperature update every 20 seconds:

.. code-block:: bash

    uc-cmd set_prop -i temp1 -p update_interval -v 20 -y

Connecting a motion sensor
--------------------------

Configure the sensorc controller to send :doc:`/snmp_traps` to our server IP,
switch on a debugging mode and look into a log file:

.. code-block:: bash

    uc-cmd debug
    tail -f log/uc.log|grep "snmp trap data"

let someone walk near the sensor and we'll catch SNMP trap data:

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

as we can see, the sensor sends SNMP OID *1.3.6.1.4.1.3854.1.7.1.0 = 4* when
there is some activity and *1.3.6.1.4.1.3854.1.7.1.0 = 2* when the activity is
finished. If we disconnect the sensor from the sensorProbe, trap with the same
OID and value *7* will be received.

switch off a debugging mode

.. code-block:: bash

    uc-cmd nodebug

and create a sensor in UC:

.. code-block:: bash

    uc-cmd create_sensor -i motion1 -g security -y

append one ident var to let it parse only "it's own" traps:

.. code-block:: bash

    uc-cmd set_prop -i motion1 -p snmp_trap.ident_vars -v "1.3.6.1.4.1.3854.1.7.6.0=MD Hall" -y

and use SNMP OID *1.3.6.1.4.1.3854.1.7.1.0* to monitor it:

.. code-block:: bash

    uc-cmd set_prop -i motion1 -p snmp_trap.set_down -v 1.3.6.1.4.1.3854.1.7.1.0=7 -y
    uc-cmd set_prop -i motion1 -p snmp_trap.set_if -v 1,1:1.3.6.1.4.1.3854.1.7.1.0=4 -y
    uc-cmd set_prop -i motion1 -p snmp_trap.set_if -v 1,0:1.3.6.1.4.1.3854.1.7.1.0=2 -y

The final sensor configuration will look like:

.. code-block:: bash

    uc-cmd get_config -i motion1

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

The sensor is ready. It doesn't require any passive update script since it's
state is updated with SNMP traps by the equpment.

Connecting a hall light
-----------------------

So, now we have to connect the lamp to Denkovi IP-16R relay. Connect it
similarly to the ventilation:

.. code-block:: bash

    uc-cmd set_cvar -i REL2_CMD -v "snmpset -v2c -c private 192.168.22.4 .1.3.6.1.4.1.42505.6.2.3.1.3"
    uc-cmd set_cvar -i REL2_UPDATE_CMD -v "snmpget -v2c -c public 192.168.22.4 .1.3.6.1.4.1.42505.6.2.3.1.3"

    uc-cmd create_unit -i lamp1 -g light -y
    uc-cmd enable_actions -i lamp1

this relay returns the status of each port separately. Additionally, there is
only one connected device and, therefore, we won't create a multiupdate for the
unit and let it to update state with own update script.

Create a script named **xc/uc/lamp1_update**

.. code-block:: bash

    #!/bin/sh

    ${REL1_UPDATE_CMD}.1 | cut -d: -f2 | awk '{ print $1 }'

and the action script **xc/uc/lamp1**

.. code-block:: bash

    #!/bin/sh

    ${RELAY1_CMD}.1 i $2

Let's update a lamp state every 30 seconds:

.. code-block:: bash

    uc-cmd set_prop -i lamp1 -p update_interval -v 30 -y

In addition, let it turn off automatically after 10 mins of inactivity:

.. code-block:: bash

    uc-cmd set_prop -i lamp1 -p auto_off -v 600 -y

and enable the actions:

.. code-block:: bash

    uc-cmd set_prop -i lamp1 -p action_always_exec -v 1 -y

Now open :doc:`/uc/uc_ei`, check the setup, switch on/off the units, see how the
sensor values are updated.

API keys configuration
----------------------

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

After the new keys are added, you need to restart UC, which we'll do later.
Firstly, you should connect it to :ref:`MQTT<mqtt_>`.

Notification system configuration
---------------------------------

.. include:: skip_easy.rst

To let the item states to be transferred from UC to other controllers in real
time, configure its notification system. Connect the server to the local
:ref:`MQTT<mqtt_>`:

.. code-block:: bash

    uc-notifier create -i eva_1 -p mqtt -h localhost -s plant1 -A eva:secret -y
    uc-notifier subscribe -i eva_1 -p state -v '#' -g '#'

    uc-notifier get_config -i eva_1

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
