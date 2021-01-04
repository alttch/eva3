Core scripts
************

.. note::

   Core scripts are generally unsafe, can crash the controller and should be
   written/used with care and only in cases, when there's no alternative
   standard safe solution.

.. contents::

What are EVA ICS core scripts
=============================

* Core scripts are Python 3 scripts, which run directly inside core of the
  controller and are launched on particular events.

* Core scripts are similar to web server modules, where request and response
  data are processed by the chain of module libraries. In EVA ICS core script
  chains process events.

* All core scripts are always executed on all events. Core scripts are executed
  by alphabetical order, one by one.

* You may combine handling of the multiple events inside one core script file.

* Code of the special file **common.py** is included in all core scripts.

What are core scripts for
=========================

Core scripts are not recommended for the enterprise-level configurations, it's
a vehicle to quickly implement:

* data collection from HTTP/POST and :ref:`MQTT <mqtt_>`, without :doc:`drivers
  </drivers>`

* simple automation tasks without :doc:`/lm/lm`

* custom API methods and extensions of EVA ICS functionality.

Core script globals and functions
=================================

* All API functions of current controller are directly available to call

* **print** function is mapped to *logging.info*

* **spawn(func, \*args, \*\*kwargs)** run function in background as a controller thread

* *logging*, *time*, *json (rapidjson)* and *eva.apikey* modules are imported
  by default.

* **dir_eva** EVA ICS directory

* **event** event info name space

* **g** special name space, shared across all core scripts

* **masterkey** controller master key

* **product** controller info name space:

    * **product.code** "uc", "lm" or "sfa"
    * **product.build** current EVA ICS build

* **system_name** system name

Core script events
==================

A special core script globals name space **event** contains the event info core
script was called for:

State event
-----------

Triggered when any item (unit, sensor or lvar) changes its state (status or
value).

.. code-block:: python

   event.type == CS_EVENT_STATE

* **event.source** source item object
* **event.data** serialized item state (dict)

API event
---------

.. warning::

    API events are deprecated. Use CS_EVENT_RPC instead

Triggered when HTTP/POST request is performed on */r/cs/somepath*.

.. code-block:: python

  event.type == CS_EVENT_API

* **event.topic** relative API URI without method prefix (e.g. *tests/test1* for
  */r/cs/tests/test1*)

* **event.topic_p** uri split by '/' (list object)

* **event.data** JSON payload data (fields "k", "save", "kind" and "method" are
  reserved and removed)

* **event.k** current call API key

.. note::

   Only HTTP/POST RESTful-like API calls are supported

RPC event
---------

Replaces API events in EVA ICS 3.3.2 and above. Triggered when JSON RPC API
method starting with "cs\_" is called.

.. code-block:: python

  event.type == CS_EVENT_RPC

* **event.topic** method name, without "cs\_" prefix.
* **event.data** params

E.g. the following JSON RPC API request:

.. code:: json

    {
        "jsonrpc": "2.0",
        "method": "cs_myfunc",
        "params":
            {
                "param1": "value1",
                "param2": "value2"
            }
    }

will generate an event with *event.topic="myfunc"* and *event.data* containing
the params.

Core scripts can not return API responses. Also note that core scripts should
handle any authentication by themselves.

MQTT event
----------

Triggered when MQTT message is received and its topic matches subscribed.

To let core scripts react to MQTT events, they must be subscribed to MQTT
topics, either with SYS API method *subscribe_corescripts_mqtt* or with "eva
<controller> corescript mqtt-subscribe <topic>" console command ("+" and "#"
MQTT masks are supported).

.. code-block:: python

  event.type == CS_EVENT_MQTT

* **event.topic** MQTT topic
* **event.topic_p** topic split by '/' (list object)
* **event.data** MQTT message data
* **event.qos** MQTT message QoS
* **event.retain** is MQTT topic retained (1) or regular (0)

System event
------------

Triggered on system events

.. code-block:: python

  event.type == CS_EVENT_SYSTEM

* **event.topic** event topic:

  * **startup** triggered after controller startup
  * **shutdown** triggered before controller shutdown

.. note::

    'shutdown' event blocks controller shutdown process until all core scripts
    are completed. The script chain must finish in 30 seconds, otherwise the
    controller suicides itself and kills own process with SIGKILL signal.

Setting up packages
-------------------

See :doc:`/packages`


Logging
=======

Core script globals contain pre-defined "logger" variable, which points to
*eva.core* logger object.

.. code-block:: python

    logger.warning('This is core script')

Creating and managing core script files
========================================

* Core scripts are available for all controllers and stored in
  **xc/{controller}/cs** (e.g. **xc/uc/cs** for :doc:`/uc/uc`).

* Core script files should have *.py* extension.

* If core script code is modified, controller reloads it automatically. However
  if core script is added or deleted, it's required to either exec
  *reload_corescripts* :doc:`/sysapi` method (or *eva <controller> corescript
  reload* console command) or restart the controller.

Code examples
=============

Core script code should be always started with "if", checking event type:

.. code-block:: python

   # turn on the lights when motion sensor is triggered
   if event.type == CS_EVENT_STATE and \
      event.source.oid == 'sensor:security/motion1' and \
      event.data['value'] == '1':
        action(k=masterkey, i='unit:light/hall', s=1)

.. note::

   * Item status/value can be obtained by accessing event.source.status and
     event.source.value fields as well. However it's highly recommended to use
     event.data dict instead - it contains "fixed" state snapshot. Actual item
     state can be modified while core script is running.

   * In core scripts, item state value is always a string

.. code-block:: python

   # print API payload to logs
   if event.type == CS_EVENT_API:
     print(event.topic)
     print(event.data)

.. code-block:: python

   # update sensor state according to MQTT JSON message { "temperature": N }
   if event.type == CS_EVENT_MQTT and event.topic == 'some/device/telemetry':
     update(
      k=masterkey,
      i='sensor:env/temp1',
      s=1,
      v=json.loads(event.data)['temperature'])

