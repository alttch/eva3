Control and monitoring items
============================

Item in EVA mean any object which can be controlled or monitored.
:doc:`/uc/uc` has 2 native item types: :ref:`unit<unit>` and
:ref:`sensor<sensor>`, plus :ref:`multiupdates<multiupdate>`, which may
contain multiple items at once.

:doc:`/lm/lm` has one native item type :ref:`lvar<lvar>` (logic variable) plus
loads remote units and sensors from connected UCs. :doc:`/sfa/sfa` has no native
item types and loads everything from the connected remote controllers.

The configurations of items are stored in runtime folder, from where the
controllers loads .json files. Each item has multiple parameters which may be
predefined or customized. All customized parameters can be displayed with the
help of API list_props or :doc:`EVA console tools</cli>` In case the
configuration file settings are changed manually or by 3rd party software,
controller should be restarted to reload the configurations.

Common item parameters
----------------------

* **id** item ID, i.e. 'lamp1'. Must be unique within one controller, even if
  items are in the different groups. This makes some complications when
  designing the whole installation architecture but allows to keep EVA
  configuration and item scripts organized in a simple way and makes system
  administration and support much easier.

* **group** item group, i.e. 'hall/lamps'. Assigned at the time of the item
  creation, the group can't be changed later to avoid synchronization problems.

* **full_id** full item id (i.e. 'hall/lamps/lamp1'), read-only

* **oid** object id, unique within the whole installation, same as full_id, but
  also contains the item type: 'unit:hall/lamps/lamp1', read-only

* **description** item description

* **virtual** boolean (true/false) param which says is the item
  :doc:`virtual<virtual>` or real.

.. _unit:

Unit
----

A unit is a physical item, a device that we control. The unit is not a relay
port, a dimmer or a controlled resistor. This is an object, for example: an
electric lamp chain, a door, ventilation, a window, a pump or a boiler. 

The unit can be controlled with one relay (e. g. a lamp chain: we control the
whole chain by turning on/off the relay port) Or with several ones (controlling
i.e. the garage door often requires two relays: the first one starts the motor,
the second one chooses the direction of movement). However, the door is one
unit with "opened" or "closed" statuses.

All units are connected to :doc:`Universal Controller</uc/uc>` subsystems,
which control them and form the single "unit" with one or several
relays/programmable switches using a :doc:`control scripts</item_scripts>`. One
Universal Controller can work with multiple units, but one unit should be
connected to only one Universal Controller in order to avoid conflicts.
Nevertheless, for the reliability, one unit can be connected to several
controllers, if its state is correctly synchronized via
:ref:`MQTT<mqtt_>`.

Each unit has its unique ID, for example "lamp1". ID can include numbers,
uppercase and lowercase Latin characters and some special characters like minus
(-) or dot (.).

Unit parameters are set via configuration. The unit can be either physical or
:doc:`virtual<virtual>`.

Status of the unit state
~~~~~~~~~~~~~~~~~~~~~~~~

Status of the unit state is always an integer (a positive number or 0), and is
by default 0 - unit is "off" (inactive) and 1 - "on" (active).

The unit can have other statuses: for example, dimmer can include the status 2
- enabled at 10% of the capacity, 3 - enabled at 50% of the capacity, window
may be fully opened or 50%. In the item configuration, you may assign the label
to each status for enhancing its usability in interfaces.

Status -1 indicates that unit has an error status. It is set from the outside
or by the system itself if the unit wasn't updated for more than "expires"
(value from item config) seconds.

Value of the unit state
~~~~~~~~~~~~~~~~~~~~~~~

Sometimes it's not necesseary to create multiple new statuses for the unit. For
such cases, the unit also has a "value" parameter (which can include both
numbers and letters). For instance, the motor can be controlled by two unit
statuses - 0 and 1, i. e. turned on/off, but Its speed is set by value.  You
can also use value to control i.e. dimmers.

EVA does not use the unit value for the internal control and monitoring logic
(except your custom macros), that is why you can set it to any value or several
values separating them with a special characters for further processing.

The blank value is "null". It is not recommended to use "" (blank) value,
because such values cannot be transmitted via :ref:`MQTT<mqtt_>` correctly. In
most cases, the system itself replaces the blank value with "null".

Units in EVA hive
~~~~~~~~~~~~~~~~~

All units have oids like **unit:group/unit_id** i.e. *unit:light/room1/lamp1*

For the synchronization via :ref:`MQTT<mqtt_>`, the following subjects are used
for units

* **[space/]unit/<group>/<unit_id>/status**  unit status, integer
* **[space/]unit/<group>/<unit_id>/value**  unit value
* **[space/]unit/<group>/<unit_id>/nstatus**  new unit status (different from
  status if action is started), integer
* **[space/]unit/<group>/<unit_id>/nvalue** new unit value
* **[space/]unit/<group>/<unit_id>/action_enabled** are actions enabled for the
  unit or not (boolean, True/False)

Unit parameters
~~~~~~~~~~~~~~~

* **expires** interger value, time (seconds) after which the item state is
  considered "expired". If the item state was not updated during this period,
  the state automatically is set to -1 (error), value is deleted (set to null).
  If 'expires' param is set to 0, this feature is disabled. The minimum
  expiration step is 0.1 sec.

* **mqtt_update = "notifier:qos"** if set, the item may receive active state
  updates through the notification from the specified :ref:`MQTT
  server<mqtt_>`. Example: "eva_1:2".

* **snmp_trap** if set, the item may receive active state updates via
  :doc:`/snmp_traps`.

* **update_exec** a :doc:`script</item_scripts>` for passive update of the item
  state, "xc/uc/ITEMID_update" by default.

* **update_interval** integer value, time (seconds) interval between the calls
  for passive update of the item. Set 0 to disable passive updates. Minimum
  step is 0.1 sec.

* **update_delay** interger value, delay (in seconds) before the next call of
  the passive update, may be used to avoid multiple update scripts of the
  different
  items run simultaneously.

* **update_timeout** integer, value, time (seconds) in which the script of the
  passive update should finish its work or it will be terminated.

* **action_allow_termination** boolean, allow the currect running action
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
    then is being executed

* **action_timeout** integer, value, time (seconds) in which the script of the
  action should finish its work or it will be terminated.

* **auto_off** integer, the simple automation parameter: the command to turn the
  unit off (call an action to set status = 0) will be executed after the
  indicated period of time (in seconds) after the last action performed for
  this unit. Set 0 to disable this feature. Minimum step is 0.1 sec.

* **mqtt_control = "notifier:qos"** item gets actions through the notifications
  from the specified :ref:`MQTT server<mqtt_>`, for example "eva_1:2",
  actions should be sent to path/to/unit/control (i.e.
  unit/hall/lamps/lamp1/control) in a form of the text messages "status [value]
  [priority]". If you want to skip value, but keep priority, set it to null,
  i.e. "status 0 null 50".

* **status_labels**  "labels" used to display the unit statuses by the
  interfaces.  Labels may be changed via :doc:`/uc/uc_api` or
  :doc:`uc-cmd</cli>`, in the following way: status:number = label, i.e.
  "status:0" = "stop". By default the unit has labels "status:0" = "OFF",
  "status:1" = "ON".

* **term_kill_interval** integer, difference (in seconds) between stopping and
  forceful stopping the action or update script. Tip: sometimes it is useful to
  catch SIGTERM in the script to exit it gracefully. Cannot exceed the value of
  timeout** 2, where timeout** default timeout, set in a controller config.

* **update_exec_after_action** boolean, start passive update immediately
  after the action is completed (to ensure the unit state has been changed
  correctly)

* **update_if_action** boolean, allow or deny passive updates while the action
  is being executed

* **update_state_after_action** boolean, if action completed successfully, the
  controller assumes that its actual unit state has ben changed correctly and
  sets it without calling/waiting for the state update.

.. _sensor:

Sensor
------

The sensor value is the parameter measured by the sensor: temperature, humidity,
pressure etc.

In terms of automation the difference between the sensor item and unit item is
obvious: we change the unit state by ourselves and monitor it only for the sake
of checking the control operations, while the sensor state is being changed by
the environment.

As regards the system itself, unit and sensor are similar items: both have
status and value, the item status is monitored actively (by :doc:`/uc/uc_api`,
:ref:`MQTT message<mqtt_>`, SNMP traps) or passively (by calling the external
script).

The sensor can have 3 statuses:

* **1** sensor is working and collecting data
* **0** sensor is disabled, the value updates are ignored (this status may be
  set via API or by the user)
* **-1** sensor error ("expires" timer went off, the status was set because the
  connection with a physical sensor got lost during passive or active update
  etc), when the sensor is in this status, its value is not sent via the
  notification system to let the other components work with the last valid data.

.. note::

    The sensor error state is automatically cleared if the new value data
    arrives.

Important: the sensor error may be set even if the sensor is disabled. It means
that the disabled sensor may be switched to "error" and then to "work" mode by
the system itself. Why it works that way? According to the logic of the system,
the sensor error is an emergency situation that should affect its status even
if it is disabled and requires an immediate attention of the user. If you want
the sensor not to respond to the external state updates - set it to the
:doc:`virtual state<virtual>`

Sensors (and sometimes units) can be placed on the same detector, controller or
bus queried by the single command. EVA can use
:ref:`multiupdates<multiupdate>` in order to update several items at once.

Since the system does not control, but only monitor the sensor, it can
be easily connected to several :doc:`Universal Controllers</uc/uc>` at once if
the equipment allows making parallel queries of the state or sending the active
updates to several addresses at once.

.. note::

    The sensor doesn't set its status to '-1' on *expires* if its status is 0
    (disabled)

Sensors in EVA hive
~~~~~~~~~~~~~~~~~~~

All sensors have oids like **sensor:group/sensor_id** i.e. *sensor:temp/t1*

For the synchronization via :ref:`MQTT<mqtt_>`, the following subjects are used
for units

* **[space/]sensor/<group>/<sensor_id>/status** sensor status, integer
* **[space/]sensor/<group>/<sensor_id>/value** sensor value

Sensor parameters
~~~~~~~~~~~~~~~~~

Sensors have the same parameters as :ref:`units<unit>`, except the don't have
action_*, auto_off, mqtt_control and status_labels.

.. _lvar:

Logic variable
--------------

EVA :doc:`Logic Manager</lm/lm>` uses the logic variables (lvars) to make
decisions and organize the production cycle timers.

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
  value and -1 status) and set_time - a time when the value was set for the
  last time.

The same logic variable may be declared on several logic controllers, but the
"expires" configuration value should remain the same because each controller
processes it autonomously. The variable becomes "expired" once it is declared
as such by any controller.

.. note::

    LVar doesn't set its status to '-1' on *expires* if it's status is 0
    (disabled)

The logic variable values may be synchronized via :ref:`MQTT server<mqtt_>` or
set via API or external scripts - similar to sensors.

You can use several logic variables as timers in order to organize the
production cycles. For example, there are three cycles: the pump No.1 operates
in the first one, the pump No. 2 in the second one, and both pumps are disabled
in the third one. In order to organize such cycle, let us create three
variables: cycle1, cycle2, cycle_stop with "expires" values equal to the
duration of each cycle in seconds.

Then - in the :doc:`decision-making matrix</lm/decision_matrix>` you should
specify the rules and macros run as soon as each cycle is finished. The macros
run and stop the pumps as well as reset the timer variables of the next cycle:
as soon as cycle_stop is finished, the pump No.1 is run, the cycle1 timer
variable is reset; as soon as the cycle1 is finished, the pump No. 2 is run and
cycle2 variable is reset; as soon as cycle2 is finished, both pumps are
disabled and cycle_stop is reset.

In order to synchronize the timer values with the interfaces and the
third-party applications, use :doc:`/lm/lm_api` test command that displays the
system information, including the local time on the server on which the
controller is installed.

However, When used in industrial configurations, it is recommended to
synchronize the time on all computers without any additional software hotfixes.

LVars in EVA hive
~~~~~~~~~~~~~~~~~

All logic variables have oids like **lvar:group/lvar_id** i.e.
*lvar:service/var1*

For the synchronization via :ref:`MQTT<mqtt_>`, the following subjects are used
for units

* **[space/]lvar/<group>/<lvar_id>/status** lvar status, integer
* **[space/]lvar/<group>/<lvar_id>/value** lvar value
* **[space/]lvar/<group>/<lvar_id>/set_time** last set time (unix timestamp)
* **[space/]lvar/<group>/<lvar_id>/expires** value expiration time (seconds)

LVar parameters
~~~~~~~~~~~~~~~

As LVars behavior is simpilar to :ref:`sensors<sensor>` except the values are
set by user/system, they have the same parameters, except lvars can't be
updated via SNMP traps and can't be virtual (lvar is actually virtual by
default).

.. _lvar_examples:

Examples using LVars
~~~~~~~~~~~~~~~~~~~~

You may use lvar as a

* **Variable** To use lvar as a shared variable to exchange some information
  between the controllers, apps and SCADA interfaces, just set its value (and
  status if you want) and that's it.
* **Timer**

  * Set **expires** configuration param
  * Use **reset** to set lvar status/value to 1 and reset the expiration timer
  * Use **clear** to set lvar status to 0 and stop it reacting to expiration
    (when used with lvar which have *expires* param set, **clear** changes it's
    status instead of value)
  * Use :doc:`decision rules</lm/decision_matrix>` with the conditions
    **on_set** and **on_expire** to run the :doc:`macros</lm/macros>` when the
    timer is set/expired
* **Flag**

  * Use lvar as a simple boolean variable to exchange the information
    True/False, yes/no, enabled/disabled and etc.
  * Use **reset** to set lvar value to 1 which should be considered as *True*
  * Use **clear** to set lvar value to 0 which should be considered as *False*
  * Use **toggle** to toggle lvar value between 0 and 1
  * Use constructions like *if value('lvar_id'):* in :doc:`macros</lm/macros>`
    to determine is the 'flag' lvar set or not.

.. _multiupdate:

Multiupdates
------------

Multiupdates allow :doc:`/uc/uc` updating the state of several items with the
use of one :doc:`script</item_scripts>`. This could be reasonable in case all
items are placed on the same bus or external controller and queried by a single
command.

Multiupdate is an independant item in the system with its own configuration
and without status and value. In turn, it updates statuses of the included
items. Multiupdate can be :doc:`virtual<virtual>`.

Multiupdates in EVA hive
~~~~~~~~~~~~~~~~~~~~~~~~

All multiupdates have oids like **mu:group/mu_id** i.e.
*mu:environment/mu1*

Multiupdates don't have own state, so they are not synchronized between servers.

Multiupdate parameters
~~~~~~~~~~~~~~~~~~~~~~

Multiupdates have the same parameters as :ref:`sensors<sensor>`, except
"expires", "mqtt_update" and "snmp_trap", plus some additional:

* items = item1, item2, item3... - the list of items for updating, may be
  changed via :doc:`/uc/uc_api` and :doc:`uc-cmd</cli>` as follows:

    * **-p "item+" -v "item_id"** add item for update
    * **-p "item-" -v "item_id"** delete item
    * **-p "items" -v "item1,item2,item3..."** replace the whole list

* update_allow_check - boolean, the multiupdate will be performed only in case
  the passive state updates are currently allowed for all included items (i.e.
  if some of them run actions at this moment and have update_if_action=False,
  multiupdate will be not executed)
