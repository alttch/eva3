SFA API
**************

:doc:`SCADA Final Aggregator<sfa>` API is used to manage EVA ICS cloud and aggregated resources.

This document describes API methods for direct and JSON RPC calls. For RESTful
API look :doc:`/sfa/sfa_api_restful`.


API basics
==========

JSON RPC
--------

`JSON RPC 2.0 <https://www.jsonrpc.org/specification>`_ protocol is the primary
EVA ICS API protocol. Note that default JSON RPC result is *{ "ok": true }*
(instead of *{ "result": "OK" }* in the direct API).  There's no *{ result:
"ERROR" }* responses, as JSON RPC sends errors in "error" field.

If JSON RPC request is called without ID and server should not return a result,
it will return http response with a code *202 Accepted*.

.. note::

    JSON RPC is recommended way to use EVA ICS API, unless direct method
    calling or RESTful is really required.

JSON RPC API URL:

    **\http://<ip_address:8828>/jrpc**

JSON RPC payload encoding
~~~~~~~~~~~~~~~~~~~~~~~~~

EVA ICS supports JSON RPC payloads, encoded as generic JSON and as `MessagePack
<https://msgpack.org/>`_. MessagePack encoding works faster, requires less
bandwidth and is highly recommended to use.

To call API methods with MessagePack-encoded payloads, use *Content-Type:
application/msgpack* HTTP request header.

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

Long API calls
--------------

* Long API calls should be avoided at any cost.

* All critical action and command methods have an option to obtain action ID
  and check for the result later.

* If long API calls are performed between controllers (e.g. action methods with
  *wait* param), remote controller timeout should be always greater than max.
  expected "wait" timeout in API call, otherwise client controller will repeat
  API calls continuously, up to max **retries** for the target controller.


Direct API
----------

.. warning::

    Direct method calling is deprecated and scheduled to be removed (not
    implemented) in EVA ICS v4. Use JSON RPC API, whenever it is possible.

SFA API functions are called through URL request

    **\http://<ip_address:8828>/sfa-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

.. warning::

    It's highly not recommended to perform long API calls, calling API
    functions from JavaScript in a web browser (e.g. giving "w" param to action
    methods to wait until action finish). Web browser may repeat API call
    continuously, which may lead to absolutely unexpected behavior.

Direct API responses
~~~~~~~~~~~~~~~~~~~~

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

.. contents::

.. _sfapi_cat_general:

General functions
=================



.. _sfapi_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid API key of the controller the function is called to.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/test.req
    :response: http-examples/sfapi/test.resp

Parameters:

* **k** any valid API key

Returns:

JSON dict with system info and current API key permissions (for masterkey only { "master": true } is returned)

.. _sfapi_login:

login - log in and get authentication token
-------------------------------------------

Obtains authentication :doc:`token</api_tokens>` which can be used in API calls instead of API key.

If both **k** and **u** args are absent, but API method is called with HTTP request, which contain HTTP header for basic authorization, the function will try to parse it and log in user with credentials provided.

If authentication token is specified, the function will check it and return token information if it is valid.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/login.req
    :response: http-examples/sfapi/login.resp

Parameters:

* **k** valid API key or
* **u** user login
* **p** user password
* **a** authentication token

Returns:

A dict, containing API key ID and authentication token

.. _sfapi_logout:

logout - log out and purge authentication token
-----------------------------------------------

Purges authentication :doc:`token</api_tokens>`

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/logout.req
    :response: http-examples/sfapi/logout.resp

Parameters:

* **k** valid token


.. _sfapi_cat_item:

Item functions
==============



.. _sfapi_action:

action - create unit control action
-----------------------------------

The call is considered successful when action is put into the action queue of selected unit.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/action.req
    :response: http-examples/sfapi/action.resp

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

.. _sfapi_action_toggle:

action_toggle - toggle unit status
----------------------------------

Create unit control action to toggle its status (1->0, 0->1)

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/action_toggle.req
    :response: http-examples/sfapi/action_toggle.resp

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

.. _sfapi_disable_actions:

disable_actions - disable unit actions
--------------------------------------

Disables unit to run and queue new actions.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/disable_actions.req
    :response: http-examples/sfapi/disable_actions.resp

Parameters:

* **k** valid API key
* **i** unit id

.. _sfapi_enable_actions:

enable_actions - enable unit actions
------------------------------------

Enables unit to run and queue new actions.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/enable_actions.req
    :response: http-examples/sfapi/enable_actions.resp

Parameters:

* **k** valid API key
* **i** unit id

.. _sfapi_groups:

groups - get item group list
----------------------------

Get the list of item groups. Useful e.g. for custom interfaces.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/groups.req
    :response: http-examples/sfapi/groups.resp

Parameters:

* **k** valid API key
* **p** item type (unit [U], sensor [S] or lvar [LV])

.. _sfapi_kill:

kill - kill unit actions
------------------------

Apart from canceling all queued commands, this function also terminates the current running action.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/kill.req
    :response: http-examples/sfapi/kill.resp

Parameters:

* **k** valid API key
* **i** unit id

Returns:

If the current action of the unit cannot be terminated by configuration, the notice "pt" = "denied" will be returned additionally (even if there's no action running)

.. _sfapi_q_clean:

q_clean - clean action queue of unit
------------------------------------

Cancels all queued actions, keeps the current action running.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/q_clean.req
    :response: http-examples/sfapi/q_clean.resp

Parameters:

* **k** valid API key
* **i** unit id

.. _sfapi_result:

result - get action status or macro run result
----------------------------------------------

Checks the result of the action by its UUID or returns the actions for the specified unit or execution result of the specified macro.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/result.req
    :response: http-examples/sfapi/result.resp

Parameters:

* **k** valid API key

Optionally:

* **u** action uuid or
* **i** unit/macro oid (either uuid or oid must be specified)
* **g** filter by unit group
* **s** filter by action status: Q for queued, R for running, F for finished

Returns:

list or single serialized action object

.. _sfapi_state:

state - get item state
----------------------

State of the item or all items of the specified type can be obtained using state command.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/state.req
    :response: http-examples/sfapi/state.resp

Parameters:

* **k** valid API key
* **p** item type (unit [U], sensor [S] or lvar [LV])

Optionally:

* **i** item id
* **g** item group
* **full** return full state

.. _sfapi_state_history:

state_history - get item state history
--------------------------------------

State history of one :doc:`item</items>` or several items of the specified type can be obtained using **state_history** command.

If master key is used, method attempt to get stored state for item even if it currently doesn't present.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/state_history.req
    :response: http-examples/sfapi/state_history.resp

Parameters:

* **k** valid API key
* **a** history notifier id (default: db_1)
* **i** item oids or full ids, list or comma separated

Optionally:

* **s** start time (timestamp or ISO or e.g. 1D for -1 day)
* **e** end time (timestamp or ISO or e.g. 1D for -1 day)
* **l** records limit (doesn't work with "w")
* **x** state prop ("status" or "value")
* **t** time format ("iso" or "raw" for unix timestamp, default is "raw")
* **w** fill frame with the interval (e.g. "1T" - 1 min, "2H" - 2 hours etc.), start time is required, set to 1D if not specified
* **g** output format ("list", "dict" or "chart", default is "list")
* **c** options for chart (dict or comma separated)
* **o** extra options for notifier data request

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

.. _sfapi_terminate:

terminate - terminate action execution
--------------------------------------

Terminates or cancel the action if it is still queued

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/terminate.req
    :response: http-examples/sfapi/terminate.resp

Parameters:

* **k** valid API key
* **u** action uuid or
* **i** unit id

Returns:

An error result will be returned eitner if action is terminated (Resource not found) or if termination process is failed or denied by unit configuration (Function failed)

.. _sfapi_clear:

clear - clear lvar state
------------------------

set status (if **expires** lvar param > 0) or value (if **expires** isn't set) of a :ref:`logic variable<lvar>` to *0*. Useful when lvar is used as a timer to stop it, or as a flag to set it *False*.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/clear.req
    :response: http-examples/sfapi/clear.resp

Parameters:

* **k** valid API key
* **i** lvar id

.. _sfapi_decrement:

decrement - decrement lvar value
--------------------------------

Decrement value of a :ref:`logic variable<lvar>`. Initial value should be number

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/decrement.req
    :response: http-examples/sfapi/decrement.resp

Parameters:

* **k** valid API key
* **i** lvar id

.. _sfapi_increment:

increment - increment lvar value
--------------------------------

Increment value of a :ref:`logic variable<lvar>`. Initial value should be number

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/increment.req
    :response: http-examples/sfapi/increment.resp

Parameters:

* **k** valid API key
* **i** lvar id

.. _sfapi_reset:

reset - reset lvar state
------------------------

Set status and value of a :ref:`logic variable<lvar>` to *1*. Useful when lvar is being used as a timer to reset it, or as a flag to set it *True*.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/reset.req
    :response: http-examples/sfapi/reset.resp

Parameters:

* **k** valid API key
* **i** lvar id

.. _sfapi_set:

set - set lvar state
--------------------

Set status and value of a :ref:`logic variable<lvar>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/set.req
    :response: http-examples/sfapi/set.resp

Parameters:

* **k** valid API key
* **i** lvar id

Optionally:

* **s** lvar status
* **v** lvar value

.. _sfapi_toggle:

toggle - clear lvar state
-------------------------

set status (if **expires** lvar param > 0) or value (if **expires** isn't set) of a :ref:`logic variable<lvar>` to *0*. Useful when lvar is used as a timer to stop it, or as a flag to set it *False*.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/toggle.req
    :response: http-examples/sfapi/toggle.resp

Parameters:

* **k** valid API key
* **i** lvar id


.. _sfapi_cat_macro:

Logic control macros
====================



.. _sfapi_groups_macro:

groups_macro - get macro groups list
------------------------------------

Get the list of macros. Useful e.g. for custom interfaces.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/groups_macro.req
    :response: http-examples/sfapi/groups_macro.resp

Parameters:

* **k** valid API key

.. _sfapi_list_macros:

list_macros - get macro list
----------------------------

Get the list of all available :doc:`macros</lm/macros>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/list_macros.req
    :response: http-examples/sfapi/list_macros.resp

Parameters:

* **k** valid API key

Optionally:

* **g** filter by group
* **i** filter by controller

.. _sfapi_run:

run - execute macro
-------------------

Execute a :doc:`macro</lm/macros>` with the specified arguments.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/run.req
    :response: http-examples/sfapi/run.resp

Parameters:

* **k** valid API key
* **i** macro id

Optionally:

* **a** macro arguments, array or space separated
* **kw** macro keyword arguments, name=value, comma separated or dict
* **w** wait for the completion for the specified number of seconds
* **u** action UUID (will be auto generated if none specified)
* **p** queue priority (default is 100, lower is better)
* **q** global queue timeout, if expires, action is marked as "dead"


.. _sfapi_cat_cycle:

Logic cycles
============



.. _sfapi_get_cycle:

get_cycle - get cycle information
---------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/get_cycle.req
    :response: http-examples/sfapi/get_cycle.resp

Parameters:

* **k** valid API key
* **i** cycle id

Returns:

field "value" contains real average cycle interval

.. _sfapi_groups_cycle:

groups_cycle - get cycle groups list
------------------------------------

Get the list of cycles. Useful e.g. for custom interfaces.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/groups_cycle.req
    :response: http-examples/sfapi/groups_cycle.resp

Parameters:

* **k** valid API key

.. _sfapi_list_cycles:

list_cycles - get cycle list
----------------------------

Get the list of all available :doc:`cycles</lm/cycles>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/list_cycles.req
    :response: http-examples/sfapi/list_cycles.resp

Parameters:

* **k** valid API key

Optionally:

* **g** filter by group
* **i** filter by controller


.. _sfapi_cat_supervisor:

Supervisor functions
====================



.. _sfapi_supervisor_lock:

supervisor_lock - set supervisor API lock
-----------------------------------------

When supervisor lock is set, SFA API functions become read-only for all users, except users in the lock scope.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/supervisor_lock.req
    :response: http-examples/sfapi/supervisor_lock.resp

Parameters:

* **k** API key with *allow=supervisor* permissions
* **l** lock scope (null = any supervisor can pass, u = only owner can pass, k = all users with owner's API key can pass)
* **c** unlock/override scope (same as lock type)
* **u** lock user (requires master key)
* **p** user type (null for local, "msad" for Active Directory etc.)
* **a** lock API key ID (requires master key)

.. _sfapi_supervisor_unlock:

supervisor_unlock - clear supervisor API lock
---------------------------------------------

API key should have permission to clear existing supervisor lock

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/supervisor_unlock.req
    :response: http-examples/sfapi/supervisor_unlock.resp

Parameters:

* **k** API key with *allow=supervisor* permissions

Returns:

Successful result is returned if lock is either cleared or not set

.. _sfapi_supervisor_message:

supervisor_message - send broadcast message
-------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/supervisor_message.req
    :response: http-examples/sfapi/supervisor_message.resp

Parameters:

* **k** API key with *allow=supervisor* permissions
* **m** message text
* **u** message sender user (requires master key)
* **a** message sender API key (requires master key)


.. _sfapi_cat_remotes:

Remote controllers
==================



.. _sfapi_append_controller:

append_controller - connect remote controller via HTTP
------------------------------------------------------

Connects remote :ref:`controller<sfa_remote_c>` to the local.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/append_controller.req
    :response: http-examples/sfapi/append_controller.resp

Parameters:

* **k** API key with *master* permissions
* **u** Controller API uri (*proto://host:port*, port not required if default)
* **a** remote controller API key (\$key to use local key)

Optionally:

* **m** ref:`MQTT notifier<mqtt_>` to exchange item states in real time (default: *eva_1*)
* **s** verify remote SSL certificate or pass invalid
* **t** timeout (seconds) for the remote controller API calls
* **g** controller type ("uc" or "lm"), autodetected if none
* **save** save connected controller configuration on the disk immediately after creation

.. _sfapi_disable_controller:

disable_controller - disable connected controller
-------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/disable_controller.req
    :response: http-examples/sfapi/disable_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

Optionally:

* **save** save configuration after successful call

.. _sfapi_enable_controller:

enable_controller - enable connected controller
-----------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/enable_controller.req
    :response: http-examples/sfapi/enable_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

Optionally:

* **save** save configuration after successful call

.. _sfapi_get_controller:

get_controller - get connected controller information
-----------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/get_controller.req
    :response: http-examples/sfapi/get_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _sfapi_list_controller_props:

list_controller_props - get controller connection parameters
------------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/list_controller_props.req
    :response: http-examples/sfapi/list_controller_props.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _sfapi_list_controllers:

list_controllers - get controllers list
---------------------------------------

Get the list of all connected :ref:`controllers<sfa_remote_c>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/list_controllers.req
    :response: http-examples/sfapi/list_controllers.resp

Parameters:

* **k** API key with *master* permissions
* **g** filter by group ("uc" or "lm")

.. _sfapi_list_remote:

list_remote - get a list of items from connected controllers
------------------------------------------------------------

Get a list of the items loaded from the connected controllers. Useful to debug the controller connections.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/list_remote.req
    :response: http-examples/sfapi/list_remote.resp

Parameters:

* **k** API key with *master* permissions

Optionally:

* **i** controller id
* **g** filter by item group
* **p** filter by item type

.. _sfapi_matest_controller:

matest_controller - test management API connection to remote controller
-----------------------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/matest_controller.req
    :response: http-examples/sfapi/matest_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _sfapi_reload_controller:

reload_controller - reload controller
-------------------------------------

Reloads items from connected controller. If controller ID "ALL" is specified, all connected controllers are reloaded.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/reload_controller.req
    :response: http-examples/sfapi/reload_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _sfapi_remove_controller:

remove_controller - disconnect controller
-----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/remove_controller.req
    :response: http-examples/sfapi/remove_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _sfapi_set_controller_prop:

set_controller_prop - set controller connection parameters
----------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/set_controller_prop.req
    :response: http-examples/sfapi/set_controller_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call

.. _sfapi_test_controller:

test_controller - test connection to remote controller
------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/test_controller.req
    :response: http-examples/sfapi/test_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _sfapi_upnp_rescan_controllers:

upnp_rescan_controllers - rescan controllers via UPnP
-----------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/upnp_rescan_controllers.req
    :response: http-examples/sfapi/upnp_rescan_controllers.resp

Parameters:

* **k** API key with *master* permissions


.. _sfapi_cat_clients:

Connected clients
=================



.. _sfapi_notify_restart:

notify_restart - notify connected clients about server restart
--------------------------------------------------------------

Sends a **server restart** event to all connected clients asking them to prepare for server restart.

All the connected clients receive the event with *subject="server"* and *data="restart"*. If the clients use :ref:`js_framework`, they can catch *server.restart* event.

Server restart notification is sent automatically to all connected clients when the server is restarting. This API function allows to send server restart notification without actual server restart, which may be useful e.g. for testing, handling frontend restart etc.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/notify_restart.req
    :response: http-examples/sfapi/notify_restart.resp

Parameters:

* **k** API key with *master* permissions

.. _sfapi_reload_clients:

reload_clients - ask connected clients to reload
------------------------------------------------

Sends **reload** event to all connected clients asking them to reload the interface.

All the connected clients receive the event with *subject="reload"* and *data="asap"*. If the clients use :ref:`js_framework`, they can catch *server.reload* event.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sfapi/reload_clients.req
    :response: http-examples/sfapi/reload_clients.resp

Parameters:

* **k** API key with *master* permissions

