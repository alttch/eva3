Universal Controller
====================

EVA Universal Controller (UC) is a control and monitoring subsystem.

It should be installed if you actually want to control something. You can use it
independently (not involving other subsystems). UC is controlled via 
:doc:`uc_ei` web interface or :doc:`uc-cmd</cli>` console application.
Additionally, it can be integrated into other subsystems and third-party
programs using :doc:`uc_api`.

:doc:`Units</items>` receive control actions, the controller forms them into
:ref:`queues<queues>` and executes them using an external scripts. If necessary,
it terminates the current script and keeps the command history.

Additionally, Universal Controller collects the data from the connected
:doc:`items</items>` using active and passive status updates.

Item status and values are stored in the local database. Other subsystems
or third-party programs can read them using :doc:`uc_api`.

Units and sensors are controlled via :doc:`uc_ei` interface,
:doc:`configured</item_configurations>` via :doc:`uc_api`. States are
controlled and updated using :doc:`item scripts</item_scripts>`.

All changes of item status, current control commands, and progress logs are
sent to the :doc:`notification system</notifiers>`.

UC POLL DELAY
-------------

EVA is a real-time system. Being one of its essential components, UC also
follows this rule. The value of polldelay is set in the configuration in seconds
(milliseconds using dot), e. g. 0.01.

The value of POLL DELAY means that all timeouts and events in the system should
fulfill their functions for not more than TIME_SET + POLL DELAY.

Reducing POLL DELAY will increase the CPU load on the server; in turn, if
increased, the UC reaction time will be longer. Recommended values: 0.1 for
home and office, 0.01 and less - for industrial applications.

The optimum value of POLL DELAY for UC can be set via :doc:`uc-cmd</cli>`, or by
manually calling :doc:`uc_api` functions and comparing reaction/execution time
of the commands.

The minimum value of POLL DELAY is 0.001 (1 millisecond).

etc/uc.ini configuration file
-----------------------------

uc.ini - basic configuration file of UC server

.. literalinclude:: ../../etc/uc.ini-dist
    :language: ini

runtime/uc_cvars.json variables file
------------------------------------

uc_cvars.json - file containing user variables passed to all commands and
:doc:`item scripts</items_scripts>` within the system environment.

File - normal JSON directory, format:

.. code-block:: json

    {
     "VAR1": "value1",
     "VAR2": "value2"
     ..............
    }

Variables can be changed while the server is run via :doc:`/sys_api` as well as
:doc:`uc-cmd</cli>` get_cvar and set_cvar commands.

For example, let's create a variable:

.. code-block:: bash

    uc-cmd set_cvar -i RELAY1_CMD -v "snmpset -v1 -c private 192.168.1.208 .1.3.6.1.4.1.19865.1.2."

After UC is started, it will become available for the system environment, and
unit management script on the port 2 of the given relay will be the following:

.. code-block:: bash

    #!/bin/sh
    ${RELAY1_CMD}.1.2.0 i $2

It's possible to assign the different values for the variables used for the
different object groups with the same names, i.e. group1/VAR1, group2/VAR1 etc.
In this case the variable will be available only for the specified group.

etc/uc_apikeys.ini API keys file
--------------------------------

API access keys are stored into etc/uc_apikeys.ini file. At least one full
access key named masterkey should be present for proper functioning. Important:
with master key and API anyone can receive the full access to the system 
similar to root user or the user UC is run under), that is why it is recommended
to use this key only in supervisory networks or even restrict it's use to local
host only.

.. literalinclude:: ../../etc/uc_apikeys.ini-dist
    :language: ini

.. _queues:

Action queues
-------------

All the unit control actions are queued right after they're created. Item status
update actions are not queued and just run in accordance with the set intervals.

Before execution the control action is placed in two queues:

* global queue for all actions
* certain unit queue

All actions have their "priority" set when they are generated. The default
priority is 100. The lower means the higher priority of queued action execution.

Queued action can have the following statuses:

* created - action has just been created and has not been queued yet
* pending - the action is placed in the global queue. The previous action
  status, as well as this one, are rarely found because :doc:`uc_api` waits for
  the command to be placed in the queue of a certain unit and then returns the
  result
* queued - the action has already passed the global queue and is now waiting to
  be executed in the queue of a certain unit
* refused - unit rejected the action execution because the item configuration
  value *action_enabled = False*
* dead - API failed to wait until the action is placed to the queue of a
  certain unit and, therefore, marked it as "dead". Virtually, such status
  clearly indicates that server is seriously overloaded
* canceled  - the command is canceled either from the outside or due to either
  unit already running the other action (in case *action_queue = 0* and queue
  is disabled) or the unit got new action to execute and *action_queue = 2*
  (cancel and terminate the pending actions after getting a new one)
* ignored - the unit rejected the action execution, because its status/value are
  the same as requested to be changed to, and *action_always_exec = False*
* running - the action is being executed
* failed - the controller failed to execute the command
* terminated - the controller terminated the action execution due to timeout or
  by the external request
* completed - the action finished successfully

Startup and shutdown
--------------------

To manage UC server use ./sbin/uc-control script with the following options:

* start - start UC server
* stop - stop UC server
* restart - restart UC server
* logrotate - call after log rotatino to restart the logging
* version - display the server version

