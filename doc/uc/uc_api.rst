UC API
**************

:doc:`Universal Controller<uc>` API is used to control and manage units and sensors

API basics
==========

Standard API (direct function calling)
--------------------------------------

UC API functions are called through URL request

    **\http://<ip_address:8812>/uc-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

All API functions can be called using GET and POST. When POST is used, the
parameters can be passed to functions either as multipart/form-data or as JSON.

API key can be sent in request parameters, session (if enabled and user is
logged in) or in HTTP **X-Auth-Key** header.

Standard API responses
~~~~~~~~~~~~~~~~~~~~~~

**Standard responses in status/body:**

* **200 OK** *{ "result": "OK" }* API call completed successfully.

**Standard error responses in status:**

* **400 Bad Request** Invalid request params
* **403 Forbidden** the API key has no access to this function or resource
* **404 Not Found** method or resource/object doesn't exist
* **405 Method Not Allowed** API function/method not found or HTTP method is
  not either GET or POST
* **409 Conflict** resource/object already exists or is locked
* **500 API Error** API function execution has been failed. Check input
  parameters and server logs.

In case API function has been failed, response body will contain JSON data with
*_error* field, which contains error message.

.. code-block:: json

    {
        "_error": "unable to add object, already present",
        "result": "ERROR"
    }

RESTful API
-----------

Majority EVA ICS API components and items support `REST
<https://en.wikipedia.org/wiki/Representational_state_transfer>`_. Parameters
for *POST, PUT, PATCH* and *DELETE* requests can be sent in both JSON and
multipart/form-data. For JSON, *Content-Type: application/json* header must be
specified.

RESTful API responses
~~~~~~~~~~~~~~~~~~~~~~

**Success responses:**

* **200 OK** API call completed successfully
* **201 Created** API call completed successfully, Response header
  *Location* contains either uri to the newly created object or resource is
  accessible by the effective request uri. For resources created with *PUT*,
  body contains either serialized resource object or resource type and id
* **202 Accepted** The server accepted command and will process it later.
* **204 No Content** API call completed successfully, no content to return

**Error error responses:**

* **403 Forbidden** the API key has no access to this function or resource
* **404 Not Found** resource doesn't exist
* **405 Method Not Allowed** API function/method not found
* **409 Conflict** resource/object already exists or is locked
* **500 API Error** API function execution has been failed. Check
  input parameters and server logs.

Response body may contain additional information encoded in JSON. *{
"result": "OK" }* and *{ "result": "ERROR" }* in body are not returned.

JSON RPC
--------

Additionally, API supports `JSON RPC 2.0
<https://www.jsonrpc.org/specification>`_ protocol. JSON RPC doesn't support
sessions, so user authorization is not possible. Also note that default JSON
RPC result is *{ "ok": true }* (instead of *{ "result": "OK" }*). There's no
error result, as JSON RPC sends errors in "error" field.

If JSON RPC request is called without ID and server should not return a result,
it will return http response with a code *202 Accepted*.

JSON RPC API URL:

    **\http://<ip_address:8812>/jrpc**

.. contents::

.. _ucapi_cat_general:

General functions
=================



.. _ucapi_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid API key of the controller the function is called to.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/test.req
    :response: http-examples/ucapi/test.resp

Parameters:

* **k** any valid API key

Returns:

JSON dict with system info and current API key permissions (for masterkey only { "master": true } is returned)

**RESTful:**

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/test.rest
    :response: http-examples/ucapi/test.resp-rest


.. _ucapi_cat_item:

Item functions
==============



.. _ucapi_action:

action - create unit control action
-----------------------------------

The call is considered successful when action is put into the action queue of selected unit.

Parameters:

* **k** 
* **i** unit id
* **s** desired unit status

Optionally:

* **v** desired unit value
* **w** wait for the completion for the specified number of seconds
* **u** action UUID (will be auto generated if none specified)
* **p** queue priority (default is 100, lower is better)
* **q** global queue timeout, if expires, action is marked as "dead"

Returns:

Serialized action object. If action is marked as dead, an error is returned (exception raised)

.. _ucapi_action_toggle:

action_toggle - create unit control action
------------------------------------------

The call is considered successful when action is put into the action queue of selected unit.

Parameters:

* **k** 
* **i** unit id

Optionally:

* **w** wait for the completion for the specified number of seconds
* **u** action UUID (will be auto generated if none specified)
* **p** queue priority (default is 100, lower is better)
* **q** global queue timeout, if expires, action is marked as "dead"

Returns:

Serialized action object. If action is marked as dead, an error is returned (exception raised)

.. _ucapi_disable_actions:

disable_actions - disable unit actions
--------------------------------------

Disables unit to run and queue new actions.

Parameters:

* **k** 
* **i** unit id

.. _ucapi_enable_actions:

enable_actions - enable unit actions
------------------------------------

Enables unit to run and queue new actions.

Parameters:

* **k** 
* **i** unit id

.. _ucapi_groups:

groups - get item group list
----------------------------

Get the list of item groups. Useful e.g. for custom interfaces.

Parameters:

* **k** 
* **p** item type (unit [U] or sensor [S])

.. _ucapi_kill:

kill - kill unit actions
------------------------

Apart from canceling all queued commands, this function also terminates the current running action.

Parameters:

* **k** 
* **i** unit id

Returns:

If the current action of the unit cannot be terminated by configuration, the notice "pt" = "denied" will be returned additionally (even if there's no action running)

.. _ucapi_q_clean:

q_clean - clean action queue of unit
------------------------------------

Cancels all queued actions, keeps the current action running.

Parameters:

* **k** 
* **i** unit id

.. _ucapi_result:

result - get action status
--------------------------

Checks the result of the action by its UUID or returns the actions for the specified unit.

Parameters:

* **k** 
* **u** action uuid or
* **i** unit id

Optionally:

* **g** filter by unit group
* **s** filter by action status: Q for queued, R for running, F for finished
* **Return** list or single serialized action object

.. _ucapi_state:

state - get item group list
---------------------------

Get the list of item groups. Useful e.g. for custom interfaces.

Parameters:

* **k** 
* **p** item type (unit [U] or sensor [S])

Optionally:

* **i** item id
* **g** item group
* **full** return full state

.. _ucapi_state_history:

state_history - get item state history
--------------------------------------

State history of one :doc:`item</items>` or several items of the specified type can be obtained using **state_history** command.

Parameters:

* **k** 
* **a** history notifier id (default: db_1)
* **i** item oids or full ids, list or comma separated

Optionally:

* **s** start time (timestamp or ISO)
* **e** end time (timestamp or ISO)
* **l** records limit (doesn't work with "w")
* **x** state prop ("status" or "value")
* **t** time format("iso" or "raw" for unix timestamp, default is "raw")
* **w** fill frame with the interval (e.g. "1T" - 1 min, "2H" - 2 hours etc.), start time is required
* **g** output format ("list" or "dict", default is "list")

.. _ucapi_terminate:

terminate - terminate action execution
--------------------------------------

Terminates or cancel the action if it is still queued

Parameters:

* **k** 
* **u** action uuid or
* **i** unit id

Returns:

An error result will be returned eitner if action is terminated (Resource not found) or if termination process is failed or denied by unit configuration (Function failed)

.. _ucapi_update:

update - update the status and value of the item
------------------------------------------------

Updates the status and value of the :doc:`item</items>`. This is one of the ways of passive state update, for example with the use of an external controller. Calling without **s** and **v** params will force item to perform passive update requesting its status from update script or driver.

Parameters:

* **k** 
* **i** item id

Optionally:

* **s** item status
* **v** item value


.. _ucapi_cat_item-management:

Item management
===============



.. _ucapi_list:

list - list items
-----------------



Parameters:

* **k** API key with *master* permissions

Optionally:

* **p** filter by item type
* **g** filter by item group

Returns:

the list of all :doc:`item</items>` available

.. _ucapi_create:

create - create new item
------------------------

Creates new :doc:`item</items>`.

Parameters:

* **k** API key with *master* permissions
* **i** item oid (**type:group/id**)

Optionally:

* **g** multi-update group
* **v** virtual item (deprecated)
* **save** save multi-update configuration immediately

.. _ucapi_create_mu:

create_mu - create multi-update
-------------------------------

Creates new :ref:`multi-update<multiupdate>`.

Parameters:

* **k** API key with *master* permissions
* **i** multi-update id

Optionally:

* **g** multi-update group
* **v** virtual multi-update (deprecated)
* **save** save multi-update configuration immediately

.. _ucapi_create_sensor:

create_sensor - create new sensor
---------------------------------

Creates new :ref:`sensor<sensor>`.

Parameters:

* **k** API key with *master* permissions
* **i** sensor id

Optionally:

* **g** sensor group
* **v** virtual sensor (deprecated)
* **save** save sensor configuration immediately

.. _ucapi_create_unit:

create_unit - create new unit
-----------------------------

Creates new :ref:`unit<unit>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/create_unit.req
    :response: http-examples/ucapi/create_unit.resp

Parameters:

* **k** API key with *master* permissions
* **i** unit id

Optionally:

* **g** unit group
* **v** virtual unit (deprecated)
* **save** save unit configuration immediately

.. _ucapi_destroy:

destroy - delete item or group
------------------------------

Deletes the :doc:`item</items>` or the group (and all the items in it) from the system.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/destroy.req
    :response: http-examples/ucapi/destroy.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id
* **g** group (either item or group must be specified)

.. _ucapi_get_config:

get_config - get item configuration
-----------------------------------



Parameters:

* **k** API key with *master* permissions
* **i** item id

Returns:

complete :doc:`item</items>` configuration

.. _ucapi_list_props:

list_props - list item properties
---------------------------------

Get all editable parameters of the :doc:`item</items>` confiugration.

Parameters:

* **k** API key with *master* permissions
* **i** item id

.. _ucapi_save_config:

save_config - save item configuration
-------------------------------------

Saves :doc:`item</items>`. configuration on disk (even if it hasn't been changed)

Parameters:

* **k** API key with *master* permissions
* **i** item id

.. _ucapi_set_prop:

set_prop - set item property
----------------------------

Set configuration parameters of the :doc:`item</items>`.

Parameters:

* **k** API key with *master* permissions
* **i** item id
* **p** property name

Optionally:

* **v** property value

.. _ucapi_clone:

clone - clone item
------------------

Creates a copy of the :doc:`item</items>`.

Parameters:

* **k** API key with *master* permissions
* **i** item id
* **n** new item id

Optionally:

* **g** multi-update group
* **save** save multi-update configuration immediately

.. _ucapi_clone_group:

clone_group - clone group
-------------------------

Creates a copy of all :doc:`items</items>` from the group.

Parameters:

* **k** API key with *master* permissions
* **g** group to clone
* **n** new group to clone to

Optionally:

* **p** item ID prefix, e.g. device1. for device1.temp1, device1.fan1
* **r** iem ID prefix in the new group, e.g. device2 (both prefixes must be specified)
* **save** save configuration immediately


.. _ucapi_cat_owfs:

1-Wire bus via OWFS
===================



.. _ucapi_create_owfs_bus:

create_owfs_bus - create OWFS bus
---------------------------------

Creates (defines) :doc:`OWFS bus</owfs>` with the specified configuration.

Parameter "location" ("n") should contain the connection configuration, e.g.  "localhost:4304" for owhttpd or "i2c=/dev/i2c-1:ALL", "/dev/i2c-0 --w1" for local 1-wire bus via I2C, depending on type.

Parameters:

* **k** API key with *master* permissions
* **i** bus ID which will be used later in :doc:`PHI</drivers>` configurations, required
* **n** OWFS location
* **l** lock port on operations, which means to wait while OWFS bus is used by other controller thread (driver command)
* **t** OWFS operations timeout (in seconds, default: default timeout)
* **r** retry attempts for each operation (default: no retries)
* **d** delay between bus operations (default: 50ms)

Optionally:

* **save** save OWFS bus config after creation

Returns:

If bus with the selected ID is already defined, error is not returned and bus is recreated.

.. _ucapi_destroy_owfs_bus:

destroy_owfs_bus - delete OWFS bus
----------------------------------

Deletes (undefines) :doc:`OWFS bus</owfs>`.

.. note::

    In some cases deleted OWFS bus located on I2C may lock *libow*     library calls, which require controller restart until you can use     (create) the same I2C bus again.

Parameters:

* **k** API key with *master* permissions
* **i** bus ID

.. _ucapi_list_owfs_buses:

list_owfs_buses - list OWFS buses
---------------------------------



Parameters:

* **k** API key with *master* permissions

.. _ucapi_scan_owfs_bus:

scan_owfs_bus - scan OWFS bus
-----------------------------

Scan :doc:`OWFS bus</owfs>` for connected 1-wire devices.

Parameters:

* **k** API key with *master* permissions
* **i** bus ID

Optionally:

* **p** specified equipment type (e.g. DS18S20,DS2405), list or comma separated
* **a** Equipment attributes (e.g. temperature, PIO), list comma separated
* **n** Equipment path
* **has_all** Equipment should have all specified attributes
* **full** obtain all attributes plus values

Returns:

If both "a" and "full" args are specified. the function will examine and values of attributes specified in "a" param. (This will poll "released" bus, even if locking is set up, so be careful with this feature in production environment).

.. _ucapi_test_owfs_bus:

test_owfs_bus - test OWFS bus
-----------------------------

Verifies :doc:`OWFS bus</owfs>` checking library initialization status.

Parameters:

* **k** API key with *master* permissions
* **i** bus ID


.. _ucapi_cat_modbus:

ModBus ports
============



.. _ucapi_create_modbus_port:

create_modbus_port - create virtual ModBus port
-----------------------------------------------

Creates virtual :doc:`ModBus port</modbus>` with the specified configuration.

ModBus params should contain the configuration of hardware ModBus port. The following hardware port types are supported:

* **tcp** , **udp** ModBus protocol implementations for TCP/IP     networks. The params should be specified as:     *<protocol>:<host>[:port]*, e.g.  *tcp:192.168.11.11:502*

* **rtu**, **ascii**, **binary** ModBus protocol implementations for     the local bus connected with USB or serial port. The params should     be specified as:     *<protocol>:<device>:<speed>:<data>:<parity>:<stop>* e.g.     *rtu:/dev/ttyS0:9600:8:E:1*

Parameters:

* **k** API key with *master* permissions
* **i** virtual port ID which will be used later in :doc:`PHI</drivers>` configurations, required
* **p** ModBus params, required
* **l** lock port on operations, which means to wait while ModBus port is used by other controller thread (driver command)
* **t** ModBus operations timeout (in seconds, default: default timeout)
* **r** retry attempts for each operation (default: no retries)
* **d** delay between virtual port operations (default: 20ms)

Optionally:

* **save** save ModBus port config after creation

Returns:

If port with the selected ID is already created, error is not returned and port is recreated.

.. _ucapi_destroy_modbus_port:

destroy_modbus_port - delete virtual ModBus port
------------------------------------------------

Deletes virtual :doc:`ModBus port</modbus>`.

Parameters:

* **k** API key with *master* permissions
* **i** virtual port ID

.. _ucapi_list_modbus_ports:

list_modbus_ports - list virtual ModBus ports
---------------------------------------------



Parameters:

* **k** API key with *master* permissions
* **i** virtual port ID

.. _ucapi_test_modbus_port:

test_modbus_port - list virtual ModBus ports
--------------------------------------------

Verifies virtual :doc:`ModBus port</modbus>` by calling connect() ModBus client method.

.. note::

    As ModBus UDP doesn't require a port to be connected, API call     always returns success unless the port is locked.

Parameters:

* **k** API key with *master* permissions
* **i** virtual port ID


.. _ucapi_cat_device:

Devices
=======



.. _ucapi_create_device:

create_device - create device items
-----------------------------------

Creates the :ref:`device<device>` from the specified template.

Parameters:

* **k** API key with *allow=device* permissions
* **c** device config (*var=value*, comma separated or dict)
* **t** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Optionally:

* **save** save items configuration on disk immediately after operation

.. _ucapi_destroy_device:

destroy_device - delete device items
------------------------------------

Works in an opposite way to :ref:`ucapi_create_device` function, destroying all items specified in the template.

Parameters:

* **k** API key with *allow=device* permissions
* **c** device config (*var=value*, comma separated or dict)
* **t** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Returns:

The function ignores missing items, so no errors are returned unless device configuration file is invalid.

.. _ucapi_list_device_tpl:

list_device_tpl - list device templates
---------------------------------------

List available device templates from runtime/tpl

Parameters:

* **k** API key with *masterkey* permissions

.. _ucapi_update_device:

update_device - update device items
-----------------------------------

Works similarly to :ref:`ucapi_create_device` function but doesn't create new items, updating the item configuration of the existing ones.

Parameters:

* **k** API key with *allow=device* permissions
* **c** device config (*var=value*, comma separated or dict)
* **t** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Optionally:

* **save** save items configuration on disk immediately after operation

