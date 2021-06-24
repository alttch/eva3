Logic Manager
*************

EVA Logic Manager (LM PLC) - is a programmable logic controller.

This subsystem is designed to automatically manage hardware and decision-making
process when the metrics are changed. Unlike standard PL controllers, LM PLC is
a network-based controller, its mission is to control equipment in local
networks and work as cloud controller via the Internet.

LM PLC operations can be event-based, cycle-based, and called manually by used.

LM PLC is customized and controlled via :doc:`lm_ei` web interface or
:doc:`eva lm</cli>` (*lm-cmd*) console application. It can also be integrated
into other subsystems and third-party programs using :doc:`lm_api`.

Additionally, you can use :doc:`console applications</cli>` for better control
of the :doc:`decision-making rules<decision_matrix>`.

LM PLC additionally introduces one more control and monitoring item:
:ref:`logic variable (lvar)<lvar>`. Logic variables are used to save and
exchange system status data as well as function as flags and timers for
organizing production cycles.

Any change in the status of :ref:`units<unit>`, :ref:`sensors<sensor>` or logic
variables is analyzed by the :doc:`decision-making matrix<decision_matrix>` of
a certain LM controller. In case the rule conditions match, the controller
calls the indicated :doc:`macro<macros>` that performs the specified actions.

Logic variables statuses are stored in the local database and can be accessed
via :doc:`LM API<lm_api>` by other subsystems or third-party programs. Status
changes are sent via :doc:`notification system</notifiers>`. To let LM PLC
operate with the items of :doc:`UCs</uc/uc>` in real time, it should be
connected to :ref:`MQTT server<mqtt_>`.

Since LM PLC is a part of EVA platform, its operating principles, settings, and
configuration files generally match the other components.

.. _lm_config:

config/lm/main registry key
===========================

*config/lm/main* :doc:`registry</registry>` key contains the controller
configuration.

.. literalinclude:: ../../lib/eva/registry/defaults/config/lm/main.yml
    :language: yaml

.. _lm_cvars:

Custom variables
================

All custom variables passed to logic control :doc:`macros<macros>` as-is.

Variables can be changed while the server is running via :doc:`/sysapi` as well
as :doc:`eva lm</cli>` **cvar get** and **cvar set** commands.

.. _lm_remote_uc:

Connecting UC controllers
=========================

Logic :doc:`macros<macros>` and :doc:`decision-making matrix<decision_matrix>`
work only with the :doc:`items</items>` known to the controller, so Logic
Manager loads information about :ref:`units<unit>` and :ref:`sensors<sensor>`
from the connected :doc:`Universal Controllers</uc/uc>`.

Prior to UC connection, it is necessary to connect LM PLC to :ref:`MQTT
server<mqtt_>`, where other controllers will send the events. Logic Manager
reads the list of items and their initial status from the connected
controllers; further status monitoring is performed via MQTT. In case MQTT
server is inaccessible or has data exchange problems, states of the items are
updated on every remote controller reload (**reload_interval** prop).

To connect UC controllers you should use **eva lm** :doc:`console
command</cli>` or :doc:`lm_api` **append_controller** function.

When connecting, it is necessary to indicate minimum URI of the connected
controller and API KEY functioning either as a master key or the key with
access to certain items. If Logic Manager and UC keys are the same, the key can
be set as *$key* (\\$key in the command line). In this case, LM will use the
local key of its own configuration.

.. code-block:: bash

    eva lm controller append http://localhost:8812 -a secretkey -y

Configurations of connected controllers are stored in the following folder:
*runtime/lm_remote_uc.d/*

Logic Manager automatically loads the connected controller data (its ID) and
saves configuration to *runtime/lm_remote_uc.d/ID.json* file.

Items from remote controllers are loaded at the LM PLC start and then refreshed
with **reload_interval** frequency set individually for each connected
controller. If LM PLC fails to get the item list during loading, it will use
the existing one.

To control the list of the received items you can use *eva lm* or
:doc:`/lm/lm_api` function :ref:`list_remote<lmapi_list_remote>`:

.. code-block:: bash

    eva lm remote -p unit
    eva lm remote -p sensor

All connected controllers have the following properties that can be changed
while LM PLC is running:

* **description** optional description of the controller
* **key** API key used to access the connected controller
* **mqtt_update** :ref:`MQTT notifier<mqtt_>` through which items update their
  status
* **reload_interval**  interval (seconds) to reload the item list from the
  server, 0 - load the list only at the start
* **ssl_verify** either verify or not the SSL certificate validity when working
  through https://. May be *True* (verify) or *False* (not verify) The
  certificate is verified by default.
* **timeout** request timeout (seconds) 
* **uri** API URI of the connected controller (*proto://host:port*, without
  */uc-api/*)

Parameters are displayed with **eva lm** command or :doc:`/lm/lm`
:ref:`list_controller_props<lmapi_list_controller_props>` function, modified
with :ref:`set_controller_prop<lmapi_set_controller_prop>`. Function
:ref:`list_controllers<lmapi_list_controllers>` displays the list of all
connected controllers.

To remove the connected controller use
:ref:`remove_controller<lmapi_remove_controller>` function.

When managing the connected controllers, ID can be either the controller ID
only or the full ID in the following format: *controller_type/ID* (i.e.
*uc/controller1*).

Macro execution queues
======================

Prior to execution, the :doc:`macros<macros>` are put into global queue. The
macros are executed progressively without waiting for the completion of the
previous macro. The queue is used for reporting only and reserved for some
internal functions. If a macro is required to block execution of the other
ones, one should use :ref:`lock<macro_api_lock>` and
:ref:`unlock<macro_api_unlock>` macro functions operating similarly to
:ref:`SYS API locking<sysapi_lock>`.

The status of the macro in queue is similar to the status of the :ref:`Universal
Controller actions<uc_queues>`.

Startup and shutdown
====================

To manage LM controller server, use:

* **eva lm server start** start LM server
* **eva lm server stop** stop LM server
* **eva lm server restart** restart LM server
* **eva lm server reload** restart controller only (without watchdogs)

The controller startup/shutdown is also performed by **./sbin/eva-control**
which is configured during the :doc:`system setup</install>`.
