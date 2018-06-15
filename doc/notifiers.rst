Notification system
===================

The Notification System is embedded in all EVA subsystems. All the events of
these subsystems are sent to the notification servers via objects called
"notifiers" which contain the configuration of the notification endpoints.

Event structure
---------------

Each event includes the following data:

* **Event subject** (not to be confused with :ref:`MQTT<mqtt_>` subject)
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

action - unit and macro action events
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every time the :ref:`unit<unit>` :ref:`action<uc_action>` or :doc:`macro
action</lm/macros>` changes its :ref:`status<uc_queues>`, the notification
server receives "action" event notification.

The notification sends data similar to ones that can be obtained using UC API
:ref:`result<uc_result>` command.

log - logged event
~~~~~~~~~~~~~~~~~~

When the system or you add the record to the logs, the notification system
sends 'log' event notification. The log notification data have the following
format:

.. code-block:: text

    {
     "h": "<SYSTEM_NAME>",
     "l": <LEVEL>,
     "p": "<PRODUCT_CODE>",
     "msg": "<message body>",
     "mod": "<MODULE>",
     "th": "<MODULE_THREAD>",
     "t": <TIME(UNIX_TIMESTAMP)>
    }

* **SYSTEM_NAME** the name specified in the configuration file of controller
  (or hostname by default)
* **LEVEL** 10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR or 50 for CRITICAL
* **PRODUCT_CODE** "uc" for :doc:`/uc/uc`, "lm" for :doc:`/lm/lm`, "sfa" for
  :doc:`/sfa/sfa`
* **MODULE** a specific system module, e. g. 'unit'
* **MODULE_THREAD** the module thread, e. g. "_t_action_processor_lamp1"

Important: the system does not send the log records related to the notification
system itself. They are not visible via EI interfaces and are written
only into the local log files. This has been done for the notification system
not to send the records in cycles.

Configuring the notification endpoints
--------------------------------------

The configuration is done using the :doc:`console commands</cli>` uc-notifier
for :doc:`/uc/uc`, lm-notifier for :doc:`/lm/lm` and sfa-notifier for
:doc:`/sfa/sfa`. Therefore, even if two controllers are set up in the same
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
   
Let's test the endpoint (for mqtt the system will try to publish [space]/test)

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
  :ref:`MQTT<mqtt_>` notifiers if you want to collect the logs of the other
  controllers and have the records available locally in SFA.

Setting up MQTT QoS
~~~~~~~~~~~~~~~~~~~

You may specify different :ref:`MQTT<mqtt_>` QoS for the events with the
different subjects.

To set the same QoS for all events, use command:

    uc-notifier set_prop -p qos -v Q

    (where Q = 0, 1 or 2)

To set QoS for the specified subject, use command:

    uc-notifier set_prop -p qos.<subject> -v Q

i.e.

    uc-notifier set_prop -p qos.log -v 0

Quick facts about MQTT QoS:

* **0**  the minimum system/network load but does not guarantee the message
  delivery
* **1** guarantees the message delivery
* **2**  the maximum system/network load which provides 100% guarantee of the
  message delivery and the guarantee the particular message has been delivered
  only once and have no duplicates.

Subscribing the notifier to events
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, the new notifier is not subscribed to any events. You can
review all the subscriptions using "get_config" command.

To subscribe notifier to the new subject, run:

    uc-notifier subscribe <-p subject> [args]

    (where subject is "state", "log" or "action")

When subscribing notifier to logs, you may use optional *-l LEVEL* param (10 -
DEBUG, 20 - INFO, default, 30 - WARNING, 40 - ERROR, 50 - CRITICAL).

When subscribing notifier to state changes, you may also always specify item
types (comma separated) or use '#' for all types with *-v TYPES* param, groups
with *-g GROUPS*. Optionlly you may specify the particular items to subscribe
notifier to with *-I ITEMS*.

.. note::

    For the each "state" subscription you must specify eitner types and groups
    or item IDs.

Example:

    uc-notifier subscribe -i test2 -p state -v '#' -g 'hall/#'

subscribes the notifier to the events of the status change of all the items in
the 'hall' group subgroups.

Subscription to "action" requires the params similar to "state". Additionally,
*-a '#'* should be specified to subscribe to all the action statuses or *-a
state1,state2,state3...* to subscribe to the certain statuses of the
:ref:`queued actions:<uc_queues>`.

In example, the following command will subscribe the notifier to the events of
all failed actions:

.. code-block:: bash

    uc-notifier subscribe -i test2 -p action -v '#' -g '#' -a dead,refused,canceled,ignored,failed,terminated

Once created, the subscription can't be changed, but the new subscription to
the same subject replaces the configuration of the previous one.

To unsubscribe the notifier from the subject, run:

    uc-notifier unsubscribe [-p subject]

if the subject is not specified, the notifier will be unsubscribed from all
notification subjects.

The controller should be restarted to apply the new subscriptions
configuration.

.. _mqtt_:

MQTT (mqtt)
-----------

MQTT is a major endpoint type used to link several EVA subsystems. For
instance, it enables :doc:`/lm/lm` and :doc:`/sfa/sfa` controllers to
receive the latest item status from :doc:`/uc/uc` servers. We test and use EVA
with `mosquitto <http://mosquitto.org/>`_ server, but you can use any server
supporting `MQTT <http://mqtt.org/>`_ protocol.  As far as MQTT is the major
type of the EVA notification system, let us examine it detailed.

MQTT and state notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`Items<items>` form in MQTT a subject hive so-called "EVA hive". Hive may
have a space i.e. "plant1/" to separate several EVA systems which use the same
MQTT server.

Item is state is stored in a hive with subject *SPACE/item_type/group/item_id*
and contains the item state data and some configuration params in the
:doc:`subtopics<items>`.

MQTT and action notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:ref:`Unit<unit>` action notifications are sent to the topic

    SPACE/unit/group/UNIT_ID/action

:doc:`Logic macros</lm/macros>` action notifications are sent to the topic

    SPACE/lmacro/group/UNIT_ID/action

These messages include the serialized action information in JSON format. As
soon as action state is changed, the new notification is being sent.

MQTT and log notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~

Log messages are sent to the MQTT server as JSON with the following MQTT
subject:

    SPACE/log
    
It means that the common log subject is created for the one EVA space.

Any EVA server (usually it's a job for `/sfa/sfa`) can be a log collector, 
collecting the reports from MQTT server (space/log), pass them further via the
local notification system and have available via API. In order to enable this
function, set param *collect_logs* to true in the notifier configuration:

    sfa-notifier set_prop -i eva_1 -p collect_logs -v true

Use MQTT for updating the item states
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

MQTT is the only EVA notifier type performing two functions at once: both
sending and receiving messages.

:doc:`items` can use MQTT to change their state (for synchronization) if the
external controller can send active notifications under this protocol.

The items change their state to the state received from MQTT, if someone sends
its state update to EVA hive with "status" or "value" subtopics.

To let the item receive MQTT state updates, set its **mqtt_update**
configuration param to the local MQTT notificator ID, as well additionally
Optionally specify MQTT QoS using a semicolon (i.e. *eva_1:2*). QoS=1 is used by
default.

One item an be subscribed to the one MQTT notifier to get the state updates, but
different items on the same controller can be subscribed to the different MQTT
notifiers.

When remote controller is connected, :doc:`/lm/lm` and :doc:`/sfa/sfa` have
copies of the remote items and it's better to sync them in real time. The MQTT
notifier where state updates are received from is set in **mqtt_update**
configuration param of the connected controller, the value
**mqtt_update_default** from *lm.ini*/*sfa.ini* is used by default.

MQTT and unit actions
~~~~~~~~~~~~~~~~~~~~~

MQTT can be also used as API to send the actions to the :ref:`units<unit>`. In
order to send the action to the unit via MQTT, send the message with the
following subject: *[space]/<group>/<unit_id>/control* and the following body:

    status value priority

value and priority parameters are optional. If value should be omitted, set it
to "none".

In case you need 100% reliability, it is not recommended to control units via
MQTT, because MQTT can only guarantee that the action has been received by MQTT
server, but not by the target :doc:`/uc/uc`. Additionally, you cannot obtain
action uuid and further monitor it.

To let unit responding to MQTT control messages, set its configuration param
**mqtt_control** to the local MQTT ID. You may specify QoS as well via
semicolon, similary as for **mqtt_update**.

HTTP/POST (http-post)
---------------------

HTTP notifications can be transferred to servers which, for some reasons,
cannot work with MQTT in realtime, i.e. servers containing the third-party or
your own PHP web applications.

http-post notifier sends data to the URI specified in the configuration with
POST method, as www-form and in the following format:

* **k** notification key the remote app may use to authorize the sender
* **subject** event subject
* **data** event data array in JSON format

Your application must respond with the JSON if the event has ben porcessed
successfully:

.. code-block:: json

    { "result" : "OK" }

or if your app failed to process it:

.. code-block:: json

    { "result" : "ERROR" }


The event *data* field is always an array and may can contain either one
event or the several ones.

When EVA controllers test remote http-post endpoint, it sends the notification
with subject="test" and the remote app should respond with { "result": "OK" }.

HTTP/GET (http)
~~~~~~~~~~~~~~~

As with http-post, event notification can be transferred to the remote apps
using HTTP/GET method. In this case the only one event notification can be sent
at once.

ET notifications are similar to POST except that k (key), s (subject of the
message) and all the data fields are transferred directly in the query string.

Example:

.. code-block:: bash

    GET http://server1/notify.php?k=secretkey&s=state&group=env&id=temp1&status=1&value=29.555&type=sensor&space=office

Your application must respond with the JSON if the event has ben porcessed
successfully:

.. code-block:: json

    { "result" : "OK" }

or if your app failed to process it:

.. code-block:: json

    { "result" : "ERROR" }


When EVA controllers test remote http-post endpoint, it sends the notification
with subject="test" and the remote app should respond with { "result": "OK" }.

http notifier configuration is similar to http-post one, except that the latter
has one additional parameter: **stop_on_error**. If it's set to true, when the
multiple notifications are being sent at once, the system will stop sending
them as soon as one of the notifications fails to be delivered.

HTTP/GET (http) is the simplest type of the notification server for the
personal use. It requires neither knowledge of some additional protocols nor
JSON decoding, your app may obtain all the data from the request query string.
