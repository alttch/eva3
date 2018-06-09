Notification system
===================

The Notification System is embedded in all EVA subsystems. All the events of
these subsystems are sent to the notification servers via objects called
"notifiers" which contain the configuration of the notification endpoints.

Event structure
---------------

Each event includes the following data:

* **Event subject** (not to be confused with :ref:`MQTT<mqtt>` subject)
* **Notification space** May be used to divide the controlled structure into
  sectors, e. g. city1/office1, plant1 etc. By dividing spaces you can separate
  one EVA installation from another using the same notification server, e. g. to
  create your own multicontrol and multimonitoring systems.
* **Event data** (usually JSON dict with) data what's actually happened

Event subjects
~~~~~~~~~~~~~~

There are several event subjects in EVA. Each notification endpoint can be
subscribed either to one of them or to several ones.

state - item state change event
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The event notifications with the "state" subject are sent by :doc:`/uc/uc` and
:doc:`/lm/lm` whenever the :doc:`items<items>` change their status.

The notification sends data similar to those, one can get using
:doc:`/uc/uc_api` or :doc:`/lm/lm_api` state.  There is one difference for
:ref:`sensors:<sensor>`: the sensor having the error status (status = -1) does
not send its value data until the value is null. This was done specifically for
the logic components to work correctly with the old value until the sensor
status data is updated correctly and sensor is back online or until the data is
expired.

action - unit action events
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every time the :ref:`unit<unit>` :ref:`action<uc_action>` changes its
:ref:`status<uc_queues>`, the notification server receives "action" event
notification.

The notification sends data similar to ones that can be obtained using UC API
ref:`result<uc_result>` command.

log - logged event
~~~~~~~~~~~~~~~~~~

When the system or you add the record to the logs, the notification system
sends 'log' event notification. The log notification data have the following
format:

.. code-block:: json

    {
     "h": "SYSTEM_NAME",
     "l": LEVEL,
     "p": "PRODUCT_CODE",
     "msg": "Message body",
     "mod": "MODULE",
     "th": "MODULE_THREAD",
     "t": TIME(UNIX_TIMESTAMP)
    }

* **SYSTEM_NAME** the name specified in the configuration file of controller
  (or hostname by default)
* **LEVEL** 10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR or 50 for CRITICAL
* **PRODUCT_CODE** "uc" for :doc:`/uc/uc`, "lm" for :doc:`/lm/lm`, "sfa" for
  :doc:`/sfa/sfa/`
* **MODULE** a specific system module, e. g. 'unit'
* **MODULE_THREAD** the module thread, e. g. "_t_action_processor_lamp1"

Important: the system does not send the log records related to the notification
system itself. They are not visible via EI interfaces and are written
only into the local log files. This has been done for the notification system
not to send the records in cycles.

Configuring the notification endpoints
--------------------------------------

The configuration is done using the :doc:`console commands</cli/cli>`
uc-notifier for :doc:`/uc/uc`, lm-notifier for :doc:`/lm/lm` and sfa-notifier
for :doc:`/sfa/sfa/`. Therefore, even if two controllers are set up in the same
folder on the same server, they have different notification endpoints
configurations.

Basic Configuration
~~~~~~~~~~~~~~~~~~~

Let's play with notification system i.e. of :doc:`/uc/uc`. This command will
give us the list of notifiers, including their types, IDs, status and endpoint
target.


    # uc-notifier list

    ========        ========        ========     ========
    Type            ID              Status       Target
    ========        ========        ========     ========
    mqtt            eva_1           Enabled      eva:test@localhost:1883/lab
    ========        ========        ========     ========
   
Let's test the endpoint (for mqtt the system will try to publish [prefix]/test)

    # uc-notifier test -i eva_1
    notifier eva_1 test passed

To create the new notifier configuration, run:

    #uc-notifier create -i ID -p TYPE -s SPACE -t TIMEOUT ARGS -y

where

* **ID** the unique ID of the notifier
* **TYPE** endpoint type (http, http-post, mqtt)
* **SPACE** notification space (optional)
* **TIMEOUT** timeout (optional)
* **ARGS**

  * to create notifier configuration of http or http-post types, you should
    indicate *"-u URI"* parameter.
  * Optionally, you can immediately set *-k KEY* (optional). The key can have
    $key_value (i.e. *$operator*) to use controller's internal key. They keys
    are sent to the certain types of the custom endpoints allowing you to
    authorize the sender.
  * for mqtt endpoints: *-h MQTT_HOST*, *-P MQTT_PORT* (optional) and *-A
    username:password* (optional).

Option *"-y"* enables the notification configuration right after creation (by
default all notifiers are created as disabled)

The notifier configuration params may be viewed with *list_props* and changed
with *set_prop* notifier cli commands. To apply the changes you must restart
the controller.

Except endpoint configuration, notifiers have some additional params:

* **skip_test** if "true", the endpoint won't be tested at the controller start
  (the controller keeps the notifier active but puts error into the log)
* **notify_key** notification key for custom http endpoints
* **collect_logs** this should be set to "true" for :doc:`/sfa/sfa`
  :ref:`MQTT<mqtt>` notifiers if you want to collect the logs of the other
  controllers and have the records available locally in SFA.
