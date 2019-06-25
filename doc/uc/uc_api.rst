UC API
**************

:doc:`Universal Controller<uc>` API is used to control and manage units and sensors

This document describes API methods for direct and JSON RPC calls. For RESTful
API look :doc:`/uc/uc_api_restful`.


API basics
==========

Standard API (direct method calling)
--------------------------------------

UC API functions are called through URL request

    **\http://<ip_address:8812>/uc-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

Standard API responses
~~~~~~~~~~~~~~~~~~~~~~

Good for backward compatibility with any devices, as all API functions can be
called using GET and POST. When POST is used, the parameters can be passed to
functions either as multipart/form-data or as JSON.

API key can be sent in request parameters, session (if enabled and user is
logged in) or in HTTP **X-Auth-Key** header.

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

JSON RPC
--------

Additionally, API supports `JSON RPC 2.0
<https://www.jsonrpc.org/specification>`_ protocol. Note that default JSON RPC
result is *{ "ok": true }* (instead of *{ "result": "OK" }*). There's no error
result, as JSON RPC sends errors in "error" field.

If JSON RPC request is called without ID and server should not return a result,
it will return http response with a code *202 Accepted*.

.. note::

    JSON RPC is recommended way to use EVA ICS API, unless direct method
    calling or RESTful is really required.

JSON RPC API URL:

    **\http://<ip_address:8812>/jrpc**

JSON RPC error responses
~~~~~~~~~~~~~~~~~~~~~~~~

JSON RPC calls return error codes equal to the codes of :doc:`EVA API
Client</api_clients>`:

* **1** the item or resource is not found

* **2** access is denied with the set API key

* **6** Attempt to call undefined API method/function

* **10** API function failed (all errors not listed here fall within this
  category)

* **11** API function is called with invalid params

* **12** API function attempted to create resource which already exists and
  can't be recreated until deleted/removed

* **13** the resource is busy (in use) and can not be accessed/recreated or
  deleted at this moment

* **14** the method is not implemented in/for requested resource

Response field *"message"* may contain additional information about error.

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

.. _ucapi_login:

login - log in and get authentication token
-------------------------------------------

Obtains authentication :doc:`token</api_tokens>` which can be used in API calls instead of API key.

If both **k** and **u** args are absent, but API method is called with HTTP request, which contain HTTP header for basic authorization, the function will try to parse it and log in user with credentials provided.

If authentication token is specified, the function will check it and return token information if it is valid.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/login.req
    :response: http-examples/ucapi/login.resp

Parameters:

* **k** valid API key or
* **u** user login
* **p** user password
* **a** authentication token

Returns:

A dict, containing API key ID and authentication token

.. _ucapi_logout:

logout - log out and purge authentication token
-----------------------------------------------

Purges authentication :doc:`token</api_tokens>`

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/logout.req
    :response: http-examples/ucapi/logout.resp

Parameters:

* **k** valid token


.. _ucapi_cat_item:

Item functions
==============



.. _ucapi_action:

action - unit control action
----------------------------

The call is considered successful when action is put into the action queue of selected unit.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/action.req
    :response: http-examples/ucapi/action.resp

Parameters:

* **k** valid API key
* **i** unit id

Optionally:

* **s** desired unit status
* **v** desired unit value
* **w** wait for the completion for the specified number of seconds
* **u** action UUID (will be auto generated if none specified)
* **p** queue priority (default is 100, lower is better)
* **q** global queue timeout, if expires, action is marked as "dead"

Returns:

Serialized action object. If action is marked as dead, an error is returned (exception raised)

.. _ucapi_action_toggle:

action_toggle - toggle unit status
----------------------------------

Create unit control action to toggle its status (1->0, 0->1)

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/action_toggle.req
    :response: http-examples/ucapi/action_toggle.resp

Parameters:

* **k** valid API key
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

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/disable_actions.req
    :response: http-examples/ucapi/disable_actions.resp

Parameters:

* **k** valid API key
* **i** unit id

.. _ucapi_enable_actions:

enable_actions - enable unit actions
------------------------------------

Enables unit to run and queue new actions.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/enable_actions.req
    :response: http-examples/ucapi/enable_actions.resp

Parameters:

* **k** valid API key
* **i** unit id

.. _ucapi_groups:

groups - get item group list
----------------------------

Get the list of item groups. Useful e.g. for custom interfaces.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/groups.req
    :response: http-examples/ucapi/groups.resp

Parameters:

* **k** valid API key
* **p** item type (unit [U] or sensor [S])

.. _ucapi_kill:

kill - kill unit actions
------------------------

Apart from canceling all queued commands, this function also terminates the current running action.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/kill.req
    :response: http-examples/ucapi/kill.resp

Parameters:

* **k** valid API key
* **i** unit id

Returns:

If the current action of the unit cannot be terminated by configuration, the notice "pt" = "denied" will be returned additionally (even if there's no action running)

.. _ucapi_q_clean:

q_clean - clean action queue of unit
------------------------------------

Cancels all queued actions, keeps the current action running.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/q_clean.req
    :response: http-examples/ucapi/q_clean.resp

Parameters:

* **k** valid API key
* **i** unit id

.. _ucapi_result:

result - get action status
--------------------------

Checks the result of the action by its UUID or returns the actions for the specified unit.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/result.req
    :response: http-examples/ucapi/result.resp

Parameters:

* **k** valid API key

Optionally:

* **u** action uuid or
* **i** unit id
* **g** filter by unit group
* **s** filter by action status: Q for queued, R for running, F for finished

Returns:

list or single serialized action object

.. _ucapi_start_item_maintenance:

start_item_maintenance - start item maintenance mode
----------------------------------------------------

During maintenance mode all item updates are ignored, however actions still can be executed

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/start_item_maintenance.req
    :response: http-examples/ucapi/start_item_maintenance.resp

Parameters:

* **k** masterkey
* **i** item ID

.. _ucapi_state:

state - get item state
----------------------

State of the item or all items of the specified type can be obtained using state command.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/state.req
    :response: http-examples/ucapi/state.resp

Parameters:

* **k** valid API key
* **p** item type (unit [U] or sensor [S])

Optionally:

* **i** item id
* **g** item group
* **full** return full state

.. _ucapi_state_history:

state_history - get item state history
--------------------------------------

State history of one :doc:`item</items>` or several items of the specified type can be obtained using **state_history** command.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/state_history.req
    :response: http-examples/ucapi/state_history.resp

Parameters:

* **k** valid API key
* **a** history notifier id (default: db_1)
* **i** item oids or full ids, list or comma separated

Optionally:

* **s** start time (timestamp or ISO or e.g. 1D for -1 day)
* **e** end time (timestamp or ISO or e.g. 1D for -1 day)
* **l** records limit (doesn't work with "w")
* **x** state prop ("status" or "value")
* **t** time format("iso" or "raw" for unix timestamp, default is "raw")
* **w** fill frame with the interval (e.g. "1T" - 1 min, "2H" - 2 hours etc.), start time is required, set to 1D if not specified
* **g** output format ("list", "dict" or "chart", default is "list")
* **c** options for chart (dict or comma separated)

Returns:

history data in specified format or chart image.

For chart, JSON RPC gets reply with "content_type" and "data" fields, where content is image content type. If PNG image format is selected, data is base64-encoded.

Options for chart (all are optional):

* type: chart type (line or bar, default is line)

* tf: chart time format

* out: output format (svg, png, default is svg),

* style: chart style (without "Style" suffix, e.g. Dark)

* other options: http://pygal.org/en/stable/documentation/configuration/chart.html#options (use range_min, range_max for range, other are passed as-is)

If option "w" (fill) is used, number of digits after comma may be specified. E.g. 5T:3 will output values with 3 digits after comma.

Additionally, SI prefix may be specified to convert value to kilos, megas etc, e.g. 5T:k:3 - divide value by 1000 and output 3 digits after comma. Valid prefixes are: k, M, G, T, P, E, Z, Y.

If binary prefix is required, it should be followed by "b", e.g. 5T:Mb:3 - divide value by 2^20 and output 3 digits after comma.

.. _ucapi_stop_item_maintenance:

stop_item_maintenance - stop item maintenance mode
--------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/stop_item_maintenance.req
    :response: http-examples/ucapi/stop_item_maintenance.resp

Parameters:

* **k** masterkey
* **i** item ID

.. _ucapi_terminate:

terminate - terminate action execution
--------------------------------------

Terminates or cancel the action if it is still queued

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/terminate.req
    :response: http-examples/ucapi/terminate.resp

Parameters:

* **k** valid API key
* **u** action uuid or
* **i** unit id

Returns:

An error result will be returned eitner if action is terminated (Resource not found) or if termination process is failed or denied by unit configuration (Function failed)

.. _ucapi_update:

update - update the status and value of the item
------------------------------------------------

Updates the status and value of the :doc:`item</items>`. This is one of the ways of passive state update, for example with the use of an external controller.

.. note::

    Calling without **s** and **v** params will force item to perform     passive update requesting its status from update script or driver.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/update.req
    :response: http-examples/ucapi/update.resp

Parameters:

* **k** valid API key
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



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list.req
    :response: http-examples/ucapi/list.resp

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

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/create.req
    :response: http-examples/ucapi/create.resp

Parameters:

* **k** API key with *master* permissions
* **i** item oid (**type:group/id**)

Optionally:

* **g** item group
* **save** save multi-update configuration immediately

.. _ucapi_create_mu:

create_mu - create multi-update
-------------------------------

Creates new :ref:`multi-update<multiupdate>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/create_mu.req
    :response: http-examples/ucapi/create_mu.resp

Parameters:

* **k** API key with *master* permissions
* **i** multi-update id

Optionally:

* **g** multi-update group
* **save** save multi-update configuration immediately

.. _ucapi_create_sensor:

create_sensor - create new sensor
---------------------------------

Creates new :ref:`sensor<sensor>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/create_sensor.req
    :response: http-examples/ucapi/create_sensor.resp

Parameters:

* **k** API key with *master* permissions
* **i** sensor id

Optionally:

* **g** sensor group
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



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/get_config.req
    :response: http-examples/ucapi/get_config.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id

Returns:

complete :doc:`item</items>` configuration

.. _ucapi_list_props:

list_props - list item properties
---------------------------------

Get all editable parameters of the :doc:`item</items>` confiugration.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list_props.req
    :response: http-examples/ucapi/list_props.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id

.. _ucapi_save_config:

save_config - save item configuration
-------------------------------------

Saves :doc:`item</items>`. configuration on disk (even if it hasn't been changed)

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/save_config.req
    :response: http-examples/ucapi/save_config.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id

.. _ucapi_set_prop:

set_prop - set item property
----------------------------

Set configuration parameters of the :doc:`item</items>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/set_prop.req
    :response: http-examples/ucapi/set_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call

.. _ucapi_clone:

clone - clone item
------------------

Creates a copy of the :doc:`item</items>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/clone.req
    :response: http-examples/ucapi/clone.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id
* **n** new item id

Optionally:

* **g** group for new item
* **save** save multi-update configuration immediately

.. _ucapi_clone_group:

clone_group - clone group
-------------------------

Creates a copy of all :doc:`items</items>` from the group.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/clone_group.req
    :response: http-examples/ucapi/clone_group.resp

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

Parameter "location" ("n") should contain the connection configuration, e.g.  "localhost:4304" for owhttpd or "i2c=/dev/i2c-1:ALL", "/dev/i2c-0 --w1" for local 1-Wire bus via I2C, depending on type.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/create_owfs_bus.req
    :response: http-examples/ucapi/create_owfs_bus.resp

Parameters:

* **k** API key with *master* permissions
* **i** bus ID which will be used later in :doc:`PHI</drivers>` configurations, required
* **n** OWFS location

Optionally:

* **l** lock port on operations, which means to wait while OWFS bus is used by other controller thread (driver command)
* **t** OWFS operations timeout (in seconds, default: default timeout)
* **r** retry attempts for each operation (default: no retries)
* **d** delay between bus operations (default: 50ms)
* **save** save OWFS bus config after creation

Returns:

If bus with the selected ID is already defined, error is not returned and bus is recreated.

.. _ucapi_destroy_owfs_bus:

destroy_owfs_bus - delete OWFS bus
----------------------------------

Deletes (undefines) :doc:`OWFS bus</owfs>`.

.. note::

    In some cases deleted OWFS bus located on I2C may lock *libow*     library calls, which require controller restart until you can use     (create) the same I2C bus again.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/destroy_owfs_bus.req
    :response: http-examples/ucapi/destroy_owfs_bus.resp

Parameters:

* **k** API key with *master* permissions
* **i** bus ID

.. _ucapi_get_owfs_bus:

get_owfs_bus - get OWFS bus configuration
-----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/get_owfs_bus.req
    :response: http-examples/ucapi/get_owfs_bus.resp

Parameters:

* **k** API key with *master* permissions
* **i** bus ID

.. _ucapi_list_owfs_buses:

list_owfs_buses - list OWFS buses
---------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list_owfs_buses.req
    :response: http-examples/ucapi/list_owfs_buses.resp

Parameters:

* **k** API key with *master* permissions

.. _ucapi_scan_owfs_bus:

scan_owfs_bus - scan OWFS bus
-----------------------------

Scan :doc:`OWFS bus</owfs>` for connected 1-Wire devices.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/scan_owfs_bus.req
    :response: http-examples/ucapi/scan_owfs_bus.resp

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

Bus acquire error can be caused in 2 cases:

* bus is locked * owfs resource not initialized (libow or location problem)

.. _ucapi_test_owfs_bus:

test_owfs_bus - test OWFS bus
-----------------------------

Verifies :doc:`OWFS bus</owfs>` checking library initialization status.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/test_owfs_bus.req
    :response: http-examples/ucapi/test_owfs_bus.resp

Parameters:

* **k** API key with *master* permissions
* **i** bus ID


.. _ucapi_cat_modbus:

Modbus ports
============



.. _ucapi_create_modbus_port:

create_modbus_port - create virtual Modbus port
-----------------------------------------------

Creates virtual :doc:`Modbus port</modbus>` with the specified configuration.

Modbus params should contain the configuration of hardware Modbus port. The following hardware port types are supported:

* **tcp** , **udp** Modbus protocol implementations for TCP/IP     networks. The params should be specified as:     *<protocol>:<host>[:port]*, e.g.  *tcp:192.168.11.11:502*

* **rtu**, **ascii**, **binary** Modbus protocol implementations for     the local bus connected with USB or serial port. The params should     be specified as:     *<protocol>:<device>:<speed>:<data>:<parity>:<stop>* e.g.     *rtu:/dev/ttyS0:9600:8:E:1*

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/create_modbus_port.req
    :response: http-examples/ucapi/create_modbus_port.resp

Parameters:

* **k** API key with *master* permissions
* **i** virtual port ID which will be used later in :doc:`PHI</drivers>` configurations, required
* **p** Modbus params

Optionally:

* **l** lock port on operations, which means to wait while Modbus port is used by other controller thread (driver command)
* **t** Modbus operations timeout (in seconds, default: default timeout)
* **r** retry attempts for each operation (default: no retries)
* **d** delay between virtual port operations (default: 20ms)
* **save** save Modbus port config after creation

Returns:

If port with the selected ID is already created, error is not returned and port is recreated.

.. _ucapi_destroy_modbus_port:

destroy_modbus_port - delete virtual Modbus port
------------------------------------------------

Deletes virtual :doc:`Modbus port</modbus>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/destroy_modbus_port.req
    :response: http-examples/ucapi/destroy_modbus_port.resp

Parameters:

* **k** API key with *master* permissions
* **i** virtual port ID

.. _ucapi_get_modbus_port:

get_modbus_port - get virtual Modbus port configuration
-------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/get_modbus_port.req
    :response: http-examples/ucapi/get_modbus_port.resp

Parameters:

* **k** API key with *master* permissions
* **i** port ID

.. _ucapi_list_modbus_ports:

list_modbus_ports - list virtual Modbus ports
---------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list_modbus_ports.req
    :response: http-examples/ucapi/list_modbus_ports.resp

Parameters:

* **k** API key with *master* permissions
* **i** virtual port ID

.. _ucapi_read_modbus_port:

read_modbus_port - read Modbus register(s) from remote slave
------------------------------------------------------------

Modbus registers must be specified as list or comma separated memory addresses predicated with register type (h - holding, i - input, c - coil, d - discrete input).

Address ranges can be specified, e.g. h1000-1010,c10-15 will return values of holding registers from 1000 to 1010 and coil registers from 10 to 15

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/read_modbus_port.req
    :response: http-examples/ucapi/read_modbus_port.resp

Parameters:

* **k** API key with *master* permissions
* **p** Modbus virtual port
* **s** Slave ID
* **i** Modbus register(s)

Optionally:

* **t** max allowed timeout for the operation

.. _ucapi_test_modbus_port:

test_modbus_port - test virtual Modbus port
-------------------------------------------

Verifies virtual :doc:`Modbus port</modbus>` by calling connect() Modbus client method.

.. note::

    As Modbus UDP doesn't require a port to be connected, API call     always returns success unless the port is locked.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/test_modbus_port.req
    :response: http-examples/ucapi/test_modbus_port.resp

Parameters:

* **k** API key with *master* permissions
* **i** virtual port ID

.. _ucapi_write_modbus_port:

write_modbus_port - write Modbus register(s) to remote slave
------------------------------------------------------------

Modbus registers must be specified as list or comma separated memory addresses predicated with register type (h - holding, c - coil).

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/write_modbus_port.req
    :response: http-examples/ucapi/write_modbus_port.resp

Parameters:

* **k** API key with *master* permissions
* **p** Modbus virtual port
* **s** Slave ID
* **i** Modbus register address
* **v** register value(s) (integer or hex or list)

Optionally:

* **t** max allowed timeout for the operation

.. _ucapi_get_modbus_slave_data:

get_modbus_slave_data - get Modbus slave data
---------------------------------------------

Get data from Modbus slave memory space

Modbus registers must be specified as list or comma separated memory addresses predicated with register type (h - holding, i - input, c - coil, d - discrete input).

Address ranges can be specified, e.g. h1000-1010,c10-15 will return values of holding registers from 1000 to 1010 and coil registers from 10 to 15

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/get_modbus_slave_data.req
    :response: http-examples/ucapi/get_modbus_slave_data.resp

Parameters:

* **k** API key with *master* permissions
* **i** Modbus register(s)


.. _ucapi_cat_phi:

Physical interfaces (PHIs)
==========================



.. _ucapi_exec_phi:

exec_phi - execute additional PHI commands
------------------------------------------

Execute PHI command and return execution result (as-is). **help** command returns all available commands.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/exec_phi.req
    :response: http-examples/ucapi/exec_phi.resp

Parameters:

* **k** API key with *master* permissions
* **i** PHI id
* **c** command to exec
* **a** command argument

.. _ucapi_get_phi_ports:

get_phi_ports - get list of PHI ports
-------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/get_phi_ports.req
    :response: http-examples/ucapi/get_phi_ports.resp

Parameters:

* **k** API key with *master* permissions
* **i** PHI id

.. _ucapi_list_phi:

list_phi - list loaded PHIs
---------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list_phi.req
    :response: http-examples/ucapi/list_phi.resp

Parameters:

* **k** API key with *master* permissions
* **full** get exntended information

.. _ucapi_list_phi_mods:

list_phi_mods - get list of available PHI modules
-------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list_phi_mods.req
    :response: http-examples/ucapi/list_phi_mods.resp

Parameters:

* **k** API key with *master* permissions

.. _ucapi_load_phi:

load_phi - load PHI module
--------------------------

Loads :doc:`Physical Interface</drivers>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/load_phi.req
    :response: http-examples/ucapi/load_phi.resp

Parameters:

* **k** API key with *master* permissions
* **i** PHI ID
* **m** PHI module

Optionally:

* **c** PHI configuration
* **save** save driver configuration after successful call

.. _ucapi_modhelp_phi:

modhelp_phi - get PHI usage help
--------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/modhelp_phi.req
    :response: http-examples/ucapi/modhelp_phi.resp

Parameters:

* **k** API key with *master* permissions
* **m** PHI module name (without *.py* extension)
* **c** help context (*cfg*, *get* or *set*)

.. _ucapi_modinfo_phi:

modinfo_phi - get PHI module info
---------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/modinfo_phi.req
    :response: http-examples/ucapi/modinfo_phi.resp

Parameters:

* **k** API key with *master* permissions
* **m** PHI module name (without *.py* extension)

.. _ucapi_phi_discover:

phi_discover - discover installed equipment supported by PHI module
-------------------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/phi_discover.req
    :response: http-examples/ucapi/phi_discover.resp

Parameters:

* **k** API key with *master* permissions
* **m** PHI module name (without *.py* extension)

Optionally:

* **x** interface to perform discover on
* **w** max time for the operation

.. _ucapi_put_phi_mod:

put_phi_mod - upload PHI module
-------------------------------

Allows to upload new PHI module to *xc/drivers/phi* folder.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/put_phi_mod.req
    :response: http-examples/ucapi/put_phi_mod.resp

Parameters:

* **k** API key with *master* permissions
* **m** PHI module name (without *.py* extension)
* **c** module content

Optionally:

* **force** overwrite PHI module file if exists

.. _ucapi_set_phi_prop:

set_phi_prop - set PHI configuration property
---------------------------------------------

appends property to PHI configuration and reloads module

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/set_phi_prop.req
    :response: http-examples/ucapi/set_phi_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** PHI ID
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call

.. _ucapi_test_phi:

test_phi - test PHI
-------------------

Get PHI test result (as-is). All PHIs respond to **self** command, **help** command returns all available test commands.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/test_phi.req
    :response: http-examples/ucapi/test_phi.resp

Parameters:

* **k** API key with *master* permissions
* **m** PHI id
* **c** test command

.. _ucapi_unlink_phi_mod:

unlink_phi_mod - delete PHI module file
---------------------------------------

Deletes PHI module file, if the module is loaded, all its instances should be unloaded first.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/unlink_phi_mod.req
    :response: http-examples/ucapi/unlink_phi_mod.resp

Parameters:

* **k** API key with *master* permissions
* **m** PHI module name (without *.py* extension)

.. _ucapi_unload_phi:

unload_phi - unload PHI
-----------------------

Unloads PHI. PHI should not be used by any :doc:`driver</drivers>` (except *default*, but the driver should not be in use by any :doc:`item</items>`).

If driver <phi_id.default> (which's loaded automatically with PHI) is present, it will be unloaded as well.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/unload_phi.req
    :response: http-examples/ucapi/unload_phi.resp

Parameters:

* **k** API key with *master* permissions
* **i** PHI ID


.. _ucapi_cat_driver:

LPI and drivers
===============



.. _ucapi_assign_driver:

assign_driver - assign driver to item
-------------------------------------

Sets the specified driver to :doc:`item</items>`, automatically updating item props:

* **action_driver_config**,**update_driver_config** to the specified     configuration * **action_exec**, **update_exec** to do all operations via driver     function calls (sets both to *|<driver_id>*)

To unassign driver, set driver ID to empty/null.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/assign_driver.req
    :response: http-examples/ucapi/assign_driver.resp

Parameters:

* **k** masterkey
* **i** item ID
* **d** driver ID (if none - all above item props are set to *null*)
* **c** configuration (e.g. port number)

Optionally:

* **save** save item configuration after successful call

.. _ucapi_get_driver:

get_driver - get loaded driver information
------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/get_driver.req
    :response: http-examples/ucapi/get_driver.resp

Parameters:

* **k** API key with *master* permissions
* **i** PHI ID

.. _ucapi_list_drivers:

list_drivers - list loaded drivers
----------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list_drivers.req
    :response: http-examples/ucapi/list_drivers.resp

Parameters:

* **k** API key with *master* permissions
* **full** get exntended information

.. _ucapi_list_lpi_mods:

list_lpi_mods - get list of available LPI modules
-------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list_lpi_mods.req
    :response: http-examples/ucapi/list_lpi_mods.resp

Parameters:

* **k** API key with *master* permissions

.. _ucapi_load_driver:

load_driver - load a driver
---------------------------

Loads a :doc:`driver</drivers>`, combining previously loaded PHI and chosen LPI module.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/load_driver.req
    :response: http-examples/ucapi/load_driver.resp

Parameters:

* **k** API key with *master* permissions
* **i** LPI ID
* **m** LPI module
* **p** PHI ID

Optionally:

* **c** Driver (LPI) configuration, optional
* **save** save configuration after successful call

.. _ucapi_modhelp_lpi:

modhelp_lpi - get LPI usage help
--------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/modhelp_lpi.req
    :response: http-examples/ucapi/modhelp_lpi.resp

Parameters:

* **k** API key with *master* permissions
* **m** LPI module name (without *.py* extension)
* **c** help context (*cfg*, *action* or *update*)

.. _ucapi_modinfo_lpi:

modinfo_lpi - get LPI module info
---------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/modinfo_lpi.req
    :response: http-examples/ucapi/modinfo_lpi.resp

Parameters:

* **k** API key with *master* permissions
* **m** LPI module name (without *.py* extension)

.. _ucapi_set_driver_prop:

set_driver_prop - set driver (LPI) configuration property
---------------------------------------------------------

appends property to LPI configuration and reloads module

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/set_driver_prop.req
    :response: http-examples/ucapi/set_driver_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** driver ID
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save driver configuration after successful call

.. _ucapi_unload_driver:

unload_driver - unload driver
-----------------------------

Unloads driver. Driver should not be used by any :doc:`item</items>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/unload_driver.req
    :response: http-examples/ucapi/unload_driver.resp

Parameters:

* **k** API key with *master* permissions
* **i** driver ID


.. _ucapi_cat_device:

Devices
=======



.. _ucapi_deploy_device:

deploy_device - deploy device items from template
-------------------------------------------------

Deploys the :ref:`device<device>` from the specified template.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/deploy_device.req
    :response: http-examples/ucapi/deploy_device.resp

Parameters:

* **k** API key with *allow=device* permissions
* **t** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Optionally:

* **c** device config (*var=value*, comma separated or dict)
* **save** save items configuration on disk immediately after operation

.. _ucapi_list_device_tpl:

list_device_tpl - list device templates
---------------------------------------

List available device templates from runtime/tpl

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/list_device_tpl.req
    :response: http-examples/ucapi/list_device_tpl.resp

Parameters:

* **k** API key with *masterkey* permissions

.. _ucapi_undeploy_device:

undeploy_device - delete device items
-------------------------------------

Works in an opposite way to :ref:`ucapi_deploy_device` function, destroying all items specified in the template.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/undeploy_device.req
    :response: http-examples/ucapi/undeploy_device.resp

Parameters:

* **k** API key with *allow=device* permissions
* **t** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Optionally:

* **c** device config (*var=value*, comma separated or dict)

Returns:

The function ignores missing items, so no errors are returned unless device configuration file is invalid.

.. _ucapi_update_device:

update_device - update device items
-----------------------------------

Works similarly to :ref:`ucapi_deploy_device` function but doesn't create new items, updating the item configuration of the existing ones.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/ucapi/update_device.req
    :response: http-examples/ucapi/update_device.resp

Parameters:

* **k** API key with *allow=device* permissions
* **t** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Optionally:

* **c** device config (*var=value*, comma separated or dict)
* **save** save items configuration on disk immediately after operation

