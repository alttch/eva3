Control and monitoring items
****************************

An item in EVA means any object which can be controlled or monitored.
:doc:`/uc/uc` has 2 native item types: :ref:`unit<unit>` and
:ref:`sensor<sensor>`, plus :ref:`multi-updates<multiupdate>`, which can
contain multiple items at once.

:doc:`/lm/lm` has one native item type :ref:`lvar<lvar>` (logic variable),
additionally it loads remote units and sensors from connected UCs.
:doc:`/sfa/sfa` has no native item types and loads everything from the
connected remote controllers.

The configurations of items are stored in runtime folder, from where the
controllers loads .json files. Each item has multiple parameters which can be
predefined or customized. All customized parameters can be displayed with the
help of API list_props or :doc:`EVA console tools</cli>` In case the
configuration file settings are changed manually or by 3rd party software,
controller should be restarted to reload the configurations.

.. contents::

Common item parameters
======================

* **id** item ID, e.g. 'lamp1'. When using **simple**
  :ref:`layout<item_layout>`, must be unique within one controller, even if
  items are in different groups. This creates some complications when designing
  the whole installation architecture but allows to keep EVA configuration and
  item scripts organized in a simple way and makes system administration and
  support much easier.

* **group** item group, i.e. 'hall/lamps'. Assigned at the time of item
  creation, the group can't be changed later to avoid synchronization problems.

* **full_id** full item id (i.e. 'hall/lamps/lamp1'), read-only. Must be unique
  within one controller despite of layout used.

* **oid** object id, unique within the whole installation, same as full_id, but
  also contains the item type: 'unit:hall/lamps/lamp1', read-only

* **description** item description

.. note::

    All EVA functions, commands and parameters can accept oid as the item
    identifier.

.. _item_layout:

Item layout
===========

EVA ICS allows to use two types of item layouts: **simple** and **enterprise**.
if the system is not being used yet and there are no items created, layout can
be set in :doc:`/uc/uc` and :doc:`/lm/lm` configuration files (option within
*[server]*: *layout=<simple|enterprise>*). Otherwise you should use
*sbin/layout-converter* tool to convert **simple** layout to **enterprise**.
Inverse conversion is not possible.

Benefits of **simple** layout:

* Good to use in simple installations or in the installations where each
  component has no similar items. Each item should have its own unique ID,
  despite that items are located in different groups.

* When doing controller maintenance tasks, you can address each item by its ID
  instead of full ID or oid.

* Item configuration files are named as *<ID>.json* and can be easily located.

Benefit of **enterprise** layout: different items in different groups can have
the same IDs. Ideal for setups where multiple similar components are managed by
one controller.

In general, **simple** layout should be used only for testing and simple
temporary setups. For usage in production environment, **enterprise** layout is
always recommended.

.. _unit:

Unit
====

A unit is a physical item, a device that we control. A unit is not a relay
port, a dimmer or a controlled resistor. This is an object, for example: an
electric lamp chain, a door, ventilation, a window, a pump or a boiler. 

The unit can be controlled with one relay (e.g. a lamp chain: we control the
whole chain by turning on/off the relay port) or with several ones (controlling
e.g. a garage door often requires two relays: the first one starts the motor,
the second one chooses the direction of movement). However, a door is one
unit with "open" or "closed" statuses.

All units are connected to :doc:`Universal Controller</uc/uc>` subsystems,
which control them and form the single "unit" with one or several
relays/programmable switches using :doc:`control scripts</item_scripts>`. One
Universal Controller can work with multiple units, but one unit should be
connected to only one Universal Controller in order to avoid conflicts.
Nevertheless, for reliability, one unit can be connected to several
controllers, if its state is correctly synchronized via
:ref:`MQTT<mqtt_>`.

Each unit has its unique ID, for example "lamp1". ID can include numbers,
uppercase and lowercase Latin characters and some special characters like minus
(-) or dot (.).

Unit parameters are set via configuration.

Status of the unit state
------------------------

Status of the unit state is always an integer (a positive number or 0), and is
by default 0 - unit is "off" (inactive) and 1 - "on" (active).

A unit can have other statuses: for example, a dimmer can include status 2 -
enabled at 10% of the capacity, 3 - enabled at 50% of the capacity, window can
be fully open or 50%. In the item configuration, you can assign a label to each
status for enhancing its usability in interfaces.

Status -1 indicates that unit has an error status. It is set from the outside
or by the system itself if the unit wasn't updated for more than "expires"
(value from item config) seconds.

Value of the unit state
-----------------------

Sometimes it's not necessary to create multiple new statuses for the unit. In
such cases, the unit also has a "value" parameter (which can include both
numbers and letters). For instance, a motor can be controlled by two unit
statuses - 0 and 1, i.e. turned on/off, but Its speed is set by value. You can
also use value to control e.g. dimmers.

EVA does not use unit value for internal control and monitoring logic (except
in your custom macros), that is why you can set it to any value or several
values separating them with special characters for further processing.

Units in EVA hive
-----------------

All units have OIDs like **unit:group/unit_id** e.g. *unit:light/room1/lamp1*

For synchronization via :ref:`MQTT<mqtt_>`, the following subjects are used for
units

* **[space/]unit/<group>/<unit_id>/status**  unit status, integer
* **[space/]unit/<group>/<unit_id>/value**  unit value
* **[space/]unit/<group>/<unit_id>/nstatus**  next unit status (different from
  status if action is being executed), integer
* **[space/]unit/<group>/<unit_id>/nvalue** next unit value
* **[space/]unit/<group>/<unit_id>/action_enabled** are actions enabled for the
  unit or not (boolean, True/False)

Unit parameters
---------------

* **expires** integer value, time (seconds) after which the item state is
  considered "expired". If the item state was not updated during this period,
  the state automatically is set to -1 (error), value is deleted (set to null).
  If 'expires' param is set to 0, this feature is disabled. The minimum
  expiration step is 0.1 sec.

* **mqtt_update = "notifier:qos"** if set, the item can receive active state
  updates through notification from the specified :ref:`MQTT server<mqtt_>`.
  Example: "eva_1:2". State updates should be sent either to MQTT topics
  "path/to/unit/status" and "path/to/unit/value" or as JSON message to
  "path/to/unit". In example, to set unit "tests/unit1" status to 1:

    * MQTT topic: *unit/tests/unit1*
    * MQTT payload:

        .. code:: json

            { "status": 1 }

  There is also a configuration field *server/mqtt-update-default* which can be
  set in *config/uc/main* :doc:`registry</registry>` key (default e.g. to
  *eva_1:2*) and applied to all newly created items.

* **snmp_trap** if set, the item can receive active state updates via
  :ref:`snmp_traps`.

* **update_delay** delay in seconds before triggered update is launched

* **update_exec** a :doc:`script</item_scripts>` for passive update of the item
  state, "xc/uc/ITEMID_update" by default.

* **update_interval** integer value, time (seconds) interval between the calls
  for passive update of the item. Set 0 to disable passive updates. Minimum
  step is 0.1 sec.

* **update_timeout** integer, value, time (seconds) in which the script of the
  passive update should finish its work or it will be terminated.

* **action_allow_termination** boolean, allow currect running action
  termination by external request.

* **action_always_exec** boolean, :doc:`always execute</always_exec>` the
  actions, even if the intended status is similar to the current one

* **action_enabled** boolean, allow or deny new actions queue/execution

* **action_exec** a :doc:`script</item_scripts>` which performs the action,
  "xc/uc/ITEMID" by default.

* **action_queue={0|1|2}**

  * **0** action queue is disabled, if the action is running, new actions are
    not accepted
  * **1** action queue is enabled, all new actions are put in queue and executed
    in a normal way
  * **2** queue is disabled, new action terminates the current running one and
    then is executed

* **action_timeout** integer, value, time (seconds) in which the script of the
  action should finish its work or it will be terminated.

* **auto_off** integer, the simple automation parameter: the command to turn the
  unit off (call an action to set status = 0) will be executed after the
  indicated period of time (in seconds) after the last action performed for
  this unit. Set 0 to disable this feature. Minimum step is 0.1 sec.

* **location** you can specify units' physical location, as GPS coordinates or
  in custom format. To specify GPS coordinates, set the parameter to value
  *longitude:latitude* or *longitude:latitude:altitude*. If you choose to set
  location as GPS or some other coords, full unit state is appended with
  virtual parameters **loc_x**, **loc_y** (and if altitude is specified -
  **loc_z**). These virtual parameters are parsed automatically from location
  and can be used later e.g. to filter units by location or to put units on
  geographical map.

* **maintenance_duration** integer, if greater than zero, item can enter
  maintenance mode on the specified amount of seconds. During maintenance mode
  all item updates are ignored, however actions still can be executed. If
  *expires* property is also set, item state expire after *maintenance_end +
  expires* seconds.


* **mqtt_control = "notifier:qos"** item gets actions through notifications
  from a specified :ref:`MQTT server<mqtt_>`, for example "eva_1:2",
  actions should be sent to path/to/unit/control (e.g.
  unit/hall/lamps/lamp1/control).
 
  The message should be:
  
  * either in a form of text messages "status [value] [priority]". If you want
    to skip value, but keep priority, set it to null, i.e. "status 0 null 50".

  * or in JSON format (fields "value" and "priority" are optional):

        .. code:: json

            { "status": 1, "value": "", "priority": 100 }

* **modbus_status**, **modbus_value** update item state from :ref:`Modbus
  slave<modbus_slave>` memory space.

* **notify_events** 2 (default) - send notifications about all events, 1 -
  about state only, 0 - disable all event notifications.

* **status_labels**  "labels" used to display the unit statuses by the
  interfaces.  Labels can be changed via :doc:`/uc/uc_api` or
  :doc:`eva uc</cli>`, in the following way: status:number = label, e.g.
  "status:0" = "stop". By default the unit has labels "status:0" = "OFF",
  "status:1" = "ON". Status labels can be used as **status** param to execute
  unit actions, in this case controllers check the status match to the
  specified label (case insensitive).

* **term_kill_interval** integer, difference (in seconds) between stopping and
  forcible stopping the action or update script. Tip: sometimes it is useful to
  catch SIGTERM in the script to exit it gracefully. Cannot exceed the value of
  timeout** 2, where timeout** default timeout, set in a controller config.

* **update_exec_after_action** boolean, start passive update immediately
  after the action is completed (to ensure the unit state has been changed
  correctly)

* **update_if_action** boolean, allow or deny passive updates while the action
  is being executed

* **update_state_after_action** boolean, if action is completed successfully,
  the controller assumes that its actual unit state has been changed correctly
  and sets it without calling/waiting for the state update.

.. _sensor:

Sensor
======

The sensor value is the parameter measured by the sensor: temperature, humidity,
pressure etc.

In terms of automation the difference between sensor item and unit item is
obvious: we change the unit state by ourselves and monitor it only for the sake
of checking the control operations, while the sensor state is changed by the
environment.

Regarding the system itself, unit and sensor are similar items: both have
status and value, the item status is monitored actively (by :doc:`/uc/uc_api`,
:ref:`MQTT message<mqtt_>`, SNMP traps) or passively (by calling the external
script).

The sensor can have 3 statuses:

* **1** sensor is working and collecting data
* **0** sensor is disabled, the value updates are ignored (this status can be
  set via API or by the user)
* **-1** sensor error ("expires" timer went off, the status was set because the
  connection with a physical sensor got lost during passive or active update
  etc), when the sensor is in this status, its value is not sent via
  notification system to let other components work with the last valid data.

.. note::

    The sensor error state is automatically cleared if new value data arrives.

Important: the sensor error can be set even if the sensor is disabled. It means
that the disabled sensor can be switched to "error" and then to "work" mode by
the system itself. Why it works that way? According to the logic of the system,
the sensor error is an emergency situation that should affect its status even
if it is disabled and requires an immediate attention of the user.

Sensors (and sometimes units) can be placed on the same detector, controller or
bus queried by a single command. EVA can use :ref:`multi-updates<multiupdate>`
in order to update several items at once.

Since the system does not control, but only monitors the sensor, it can
be easily connected to several :doc:`Universal Controllers</uc/uc>` at once if
the equipment allows making parallel queries of the state or sending active
updates to several addresses at once.

.. note::

    The sensor doesn't set its status to '-1' on *expires* if its status is 0
    (disabled)

Sensors in EVA hive
-------------------

All sensors have OIDs like **sensor:group/sensor_id** e.g. *sensor:temp/t1*

For synchronization via :ref:`MQTT<mqtt_>`, the following subjects are used for
units

* **[space/]sensor/<group>/<sensor_id>/status** sensor status, integer
* **[space/]sensor/<group>/<sensor_id>/value** sensor value

Sensor parameters
-----------------

Sensors have the same parameters as :ref:`units<unit>`, except they don't have
action_*, auto_off, mqtt_control, modbus_status and status_labels.

Validation of state value
=========================

State value of units and sensors can be validated before :doc:`/uc/uc` perform
item update.

To validate item value, the following item properties are used:

* **value_in_range_max** value should be less
* **value_in_range_max_eq**  value should be less or equal than specified max.
* **value_in_range_min** value should be greater
* **value_in_range_min_eq**  value should be greater or equal than specified
  max.

or virtual parameter **value_condition**, which can be set in human readable
way, e.g. 20<x<=200.

If value validation is set and item receive state value which is not numeric or
doesn't feet the specified range, item keep previous state value and get status
*-1* (error).

Item status is set back to normal as soon as any valid state update is
received.

.. _lvar:

Logic variable
==============

EVA :doc:`Logic Manager</lm/lm>` uses the logic variables (lvars) to make
decisions and organize production cycle timers.

The parameters of logic variables are set in their configurations.

Actually lvars are similar to sensors, but with the following differences:

* The system architecture implies that the sensor value is changed depending on
  the environment; the logic variables are set by the user or the system
  itself. 
* The logic variables, as well as the sensors, have statuses -1, 0 and 1.
  However, if the status is 0 (variable is disabled) it stops responding to any
  value-only changes.
* The logic variables exchange two more parameters with the notification system:
  "expires" (time in seconds after the variable is set, and then takes the null
  value and -1 status) and set_time - time when the value was set for the last
  time.

The same logic variable can be declared on several logic controllers, but the
"expires" configuration value should remain the same because each controller
processes it autonomously. The variable becomes "expired" once it is declared
as such by any controller.

.. note::

    LVar doesn't set its status to '-1' on *expires* if its status is 0
    (disabled)

The logic variable values can be synchronized via :ref:`MQTT server<mqtt_>` or
set via API or external scripts - similar to sensors.

You can use several logic variables as timers in order to organize production
cycles. For example, there are three cycles: the pump No.1 operates in the
first one, the pump No. 2 in the second one, and both pumps are disabled in the
third one. In order to organize such cycle, let us create three variables:
cycle1, cycle2, cycle_stop with "expires" values equal to the duration of each
cycle in seconds.

Then - in the :doc:`decision-making matrix</lm/decision_matrix>` you should
specify the rules and macros run as soon as each cycle is finished. The macros
run and stop the pumps as well as reset the timer variables of the next cycle:
as soon as cycle_stop is finished, the pump No.1 is run, the cycle1 timer
variable is reset; as soon as the cycle1 is finished, the pump No. 2 is run and
cycle2 variable is reset; as soon as cycle2 is finished, both pumps are
disabled and cycle_stop is reset.

In order to synchronize timer values with interfaces and the third-party
applications, use :doc:`/lm/lm_api` test command that displays the system
information, including local time on the server on which the controller is
installed.

However, when used in industrial configurations, it is recommended to
synchronize time on all computers without any additional software hotfixes.

LVars in EVA hive
-----------------

All logic variables have OIDs like **lvar:group/lvar_id** e.g.
*lvar:service/var1*

For synchronization via :ref:`MQTT<mqtt_>`, the following subjects are used for
units

* **[space/]lvar/<group>/<lvar_id>/status** lvar status, integer
* **[space/]lvar/<group>/<lvar_id>/value** lvar value
* **[space/]lvar/<group>/<lvar_id>/set_time** last set time (Unix timestamp)
* **[space/]lvar/<group>/<lvar_id>/expires** value expiration time (seconds)

.. _lvar_examples:

Examples using LVars
--------------------

You can use lvar as a

* **Variable** To use lvar as a shared variable to exchange some information
  between controllers, apps and SCADA interfaces, just set its value (and
  status if you want) and that's it.

* **Timer**

  * Set **expires** configuration param
  * Use **reset** to set lvar status/value to 1 and reset the expiration timer
  * Use **clear** to set lvar status to 0 and stop it reacting to expiration
    (when used with lvar which have *expires* param set, **clear** changes its
    status instead of value)
  * Use :doc:`decision rules</lm/decision_matrix>` with the conditions
    **on_set** and **on_expire** to run the :doc:`macros</lm/macros>` when the
    timer is set/expired
  * if the timer has status set to *1*, it's running
  * if status is *0*, it's disabled with **clear** function
  * if status is *-1* and value is *null* (empty), the timer is expired

* **Flag**

  * Use lvar as a simple boolean variable to exchange the information
    True/False, yes/no, enabled/disabled etc.
  * Use **reset** to set lvar value to 1 which should be considered as *True*
  * Use **clear** to set lvar value to 0 which should be considered as *False*
  * Use **toggle** to toggle lvar value between 0 and 1
  * Use constructions like *if value('lvar_id'):* in :doc:`macros</lm/macros>`
    to determine is the 'flag' lvar is set or not.

LVar parameters
---------------

As LVars behavior is similar to :ref:`sensors<sensor>` except the values are
set by user/system, they have the same parameters, except lvars can't be
updated via SNMP traps / MQTT.

LVars also have an additional parameter *logic*.

Simple logic
------------

If lvar property *logic* is set to 'simple', it bypasses built-in logic
behavior conditions:

* LVar status can be set to any integer

* Status "0" is considered as normal and:

    * Lvar value can be updated even if LVar status is 0
    * LVar is considered as expired even if LVar status is 0

* When LVar becomes expired, its value is cleared, but the status is kept

Simple logic is useful to use LVars as simple double data holding registers
(integer + any value) for various tasks.

.. _multiupdate:

Multi-updates
=============

.. warning::

    Starting from EVA ICS 3.3.2, multi-updates are deprecated

Multi-updates allow :doc:`/uc/uc` updating the state of several items with the
use of one :doc:`script</item_scripts>`. This could be reasonable in case all
items are placed on the same bus or external controller and queried by a single
command.

Multi-update is an independent item in the system with its own configuration
and without status and value. In turn, it updates statuses of the included
items.

Multi-updates in EVA hive
-------------------------

All multi-updates have OIDs like **mu:group/mu_id** e.g.
*mu:environment/mu1*

Multi-updates don't have their own state, so they are not synchronized between
servers.

Multiupdate parameters
----------------------

Multi-updates have the same parameters as :ref:`sensors<sensor>`, except that
"expires", "mqtt_update" and "snmp_trap", plus some additional:

* items = item1, item2, item3... - the list of items for updating, can be
  changed via :doc:`/uc/uc_api` and :doc:`eva uc</cli>` as follows:

    * **-p "item+" -v "item_id"** add item for update
    * **-p "item-" -v "item_id"** delete item
    * **-p "items" -v "item1,item2,item3..."** replace the whole list

* update_allow_check - boolean, the multi-update will be performed only in case
  the passive state updates are currently allowed for all included items (i.e.
  if some of them run actions at this moment and have update_if_action=False,
  multi-update will be not executed)

.. _device:

Device
======

Multiple CVARs, units and sensors can be merged in logical groups called
**devices**. It's completely up to you how to merge items into device,
but it's recommended to keep them in one or several separate item groups.

Device templates are stored in *runtime/tpl* folder in YAML (default) or JSON
format.

You can use **uc-tpl** :doc:`command line</cli>` tool to create device
templates using the existing items and **eva uc** or :ref:`device
management<ucapi_deploy_device>` UC API functions to create, update and destroy
devices.

Device management requires master key or a key with *allow=device* permission.

.. note::

    Starting from EVA ICS 3.3.2, device template format is equal to :doc:`/iac`
    files. The old format is deprecated.

Device example
--------------

Let's imagine we have some hardware device, which has 1 relay and 2 sensors.
We have a lot of devices like this and we want to create them using template.

Create one instance of device in :doc:`/uc/uc` defining all its items:

* *sensor:device1/device1.sensor1*
* *sensor:device1/device1.sensor2*
* *unit:device1/device1.relay1*

Configure all defined items, then run:

.. code-block:: bash

    uc-tpl generate -i sensor:device1/device1.sensor1,sensor:device1/device1.sensor2,unit:device1/device1.relay1

This will output device JSON template. Use *-t* param to output template to
file or copy/paste it from the screen. You can use *-c* param to ask the tool
automatically prepare template variables, but in our example it will just
replace all *1* to *{{ ID }}*. We don't want it to be done this way because we
have *sensor1* and *relay1* items, so let's edit the template manually:

.. code-block:: json

    {
        "sensors": [
            {
                "group": "device{{ ID }}",
                "id": "device{{ ID }}.sensor1"
            },
            {
                "group": "device{{ ID }}",
                "id": "device{{ ID }}.sensor2"
            }
        ],
        "units": [
            {
                "group": "device{{ ID }}",
                "id": "device{{ ID }}.relay1"
            }
        ]
    }

(template will also contain items' configurations which are omitted in the
example)

Save the final template as *runtime/tpl/mydevice.json* folder, and then

.. code-block:: bash

    # execute this command to create new device "device5"
    eva uc device create mydevice -C ID=5 -y
    # execute this command to destroy "device5"
    eva uc device destroy mydevice -C ID=5

Configurations of the newly created items of *device5* are exact copies of the
items of *device1*. The only configuration difference is the params where we've
put template variables instead of part or full param value (in our example:
*{{ ID }}*).

.. note::

    Device templates are actually `jinja2 <http://jinja.pocoo.org/>`_
    templates, so you can use any jinja2 syntax in them (loops, conditions and
    etc.)

Device limitations
------------------

* :ref:`Custom variables<uc_cvars>`, :ref:`units<unit>`, :ref:`sensors<sensor>`
  and :ref:`multi-updates<multiupdate>` can be part of the device

* :ref:`LVars<lvar>` can not be part of the device and :doc:`/lm/lm` doesn't
  have any device management functions, but devices on the connected UCs can be
  created from :ref:`logic macros<macro_api_deploy_device>`.

Defaults
========

It is possible to re-define default initial item configuration by using
"config/uc/defaults" (for units and sensors) and "config/lm/defaults" (for
lvars) :doc:`registry</registry>` keys.

E.g. let us make units to have actions enabled by default, when created and
sensors, enabled by default (when created or when there is no state in the
state database).

.. code:: shell

    eva-registry edit eva3/$(hostname)/config/uc/defaults

.. code:: yaml

    unit:
        action_enabled: true
    sensor:
        status: 1

.. code:: shell

    eva uc server restart
    eva uc create unit:tests/unit1

.. warning::

    Changing defaults is considered as an advanced operation, if defaults are
    set to incorrect values, controllers do not create items properly.
