Control and monitoring items
============================

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

All units are connected to :doc:`Universal Controller</uc/uc.rst>` subsystems,
which control them and form the single "unit" with one or several
relays/programmable switches using a :doc:`control scripts</item_scripts>`. One
Universal Controller can work with multiple units, but one unit should be
connected to only one Universal Controller in order to avoid conflicts.
Nevertheless, for the reliability, one unit can be connected to several
controllers, if it's state is correctly synchronized via
:doc:`MQTT</notifiers>`.

Each unit has its unique ID, for example "lamp1". ID can include numbers,
uppercase and lowercase Latin characters and some special characters like minus
(-) or dot (.).

Unit parameters are set via configuration. The unit can be either physical or
:doc:`virtual</virtual_items>`.

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

Value of the unit stat
~~~~~~~~~~~~~~~~~~~~~~

Sometimes it's not necesseary to create multiple new statuses for the unit. For
such cases, the unit also has a "value" parameter (which can include both
numbers and letters). For instance, the motor can be controlled by two unit
statuses - 0 and 1, i. e. turned on/off, but Its speed is set by value.  You
can also use value to control i.e. dimmers.

EVA does not use the unit value for the internal control and monitoring logic
(except your custom macros), that is why you can set it to any value or several
values separating them with a special characters for further processing.

The blank value is "null". It is not recommended to use "" (blank) value,
because such values cannot be transmitted via MQTT correctly. In most cases,
the system itself replaces the blank value with "null".

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
MQTT message, SNMP traps) or passively (by calling the external script).

The sensor can have 3 statuses:

* 1 - sensor is working and collecting data
* 0 - sensor is disabled, the value updates are ignored (this status may be set
  via API or by the user)
* -1 - sensor error ("expires" timer went off, the status was set because the
  connection with a physical sensor got lost during passive or active update
  etc), when the sensor is in this status, it's value is not sent via the
  notification system to let the other components work with the last valid data.

.. note::

    The sensor error state is automatically cleared if the new value data
    arrives.

Important: the sensor error may be set even if the sensor is disabled. It means
that the disabled sensor may be switched to "error" and then to "work" mode by
the system itself. Why it works that way? According to the logic of the system,
the sensor error is an emergency situation that should affect it's status even
if it is disabled and requires an immediate attention of the user. If you want
the sensor not to respond to the external state updates - set it to the
:doc:`virtual state</virtual_items>`

Sensors (and sometimes units) can be placed on the same detector, controller or
bus queried by the single command. EVA can use
:doc:`multiupdates</item_scripts>` in order to update several items at once.

Since the system does not control, but only monitor the sensor, it can
be easily connected to several :doc:`Universal Controllers</uc/uc>` at once if
the equipment allows making parallel queries of the state or sending the active
updates to several addresses at once.

Logic variables
---------------

EVA :doc:`Logic Manager</lm/lm>` uses the logic variables (lvars) to make
decisions and organize the production cycle timers.

The parameters of logic variables are set in their configurations.

Actually lvars are similar to sensors, but with the following differences:

* The system architecture implies that the sensor value is changed depending on
  the environment; the logic variables are set by the user or the system
  itself. 
* The logic variables, as well as the sensors, have statuses -1, 0 and 1.
  However, if the status is 0 (variable is disabled) it stops responding to any
  changes.
* The logic variables exchange two more parameters with the notification system:
  "expires" (time in seconds after the variable is set, and then takes the null
  value and -1 status) and set_time - a time when the value was set for the
  last time.

The same logic variable may be declared on several logic controllers, but the
"expires" configuration value should remain the same because each controller
processes it autonomously. The variable becomes "expired" once it is declared
as such by any controller.

The logic variable values may be synchronized via MQTT server or set via API or
external scripts - similar to sensors.

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
