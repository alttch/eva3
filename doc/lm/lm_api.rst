LM API
**************

:doc:`Logic Manager<lm>` API is used to manage lvars, rules and other logic elements

This document describes API methods for direct and JSON RPC calls. For RESTful
API look :doc:`/lm/lm_api_restful`.


API basics
==========

Standard API (direct method calling)
--------------------------------------

LM API functions are called through URL request

    **\http://<ip_address:8817>/lm-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

.. warning::

    It's highly not recommended to perform long API calls, calling API
    functions from JavaScript in a web browser (e.g. giving "w" param to action
    methods to wait until action finish). Web browser may repeat API call
    continuously, which may lead to absolutely unexpected behavior.

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

    **\http://<ip_address:8817>/jrpc**

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

.. _lmapi_cat_general:

General functions
=================



.. _lmapi_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid API key of the controller the function is called to.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/test.req
    :response: http-examples/lmapi/test.resp

Parameters:

* **k** any valid API key

Returns:

JSON dict with system info and current API key permissions (for masterkey only { "master": true } is returned)

.. _lmapi_login:

login - log in and get authentication token
-------------------------------------------

Obtains authentication :doc:`token</api_tokens>` which can be used in API calls instead of API key.

If both **k** and **u** args are absent, but API method is called with HTTP request, which contain HTTP header for basic authorization, the function will try to parse it and log in user with credentials provided.

If authentication token is specified, the function will check it and return token information if it is valid.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/login.req
    :response: http-examples/lmapi/login.resp

Parameters:

* **k** valid API key or
* **u** user login
* **p** user password
* **a** authentication token

Returns:

A dict, containing API key ID and authentication token

.. _lmapi_logout:

logout - log out and purge authentication token
-----------------------------------------------

Purges authentication :doc:`token</api_tokens>`

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/logout.req
    :response: http-examples/lmapi/logout.resp

Parameters:

* **k** valid token


.. _lmapi_cat_lvar:

LVar functions
==============



.. _lmapi_clear:

clear - clear lvar state
------------------------

set status (if **expires** lvar param > 0) or value (if **expires** isn't set) of a :ref:`logic variable<lvar>` to *0*. Useful when lvar is used as a timer to stop it, or as a flag to set it *False*.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/clear.req
    :response: http-examples/lmapi/clear.resp

Parameters:

* **k** valid API key
* **i** lvar id

.. _lmapi_decrement:

decrement - decrement lvar value
--------------------------------

Decrement value of a :ref:`logic variable<lvar>`. Initial value should be number

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/decrement.req
    :response: http-examples/lmapi/decrement.resp

Parameters:

* **k** valid API key
* **i** lvar id

.. _lmapi_groups:

groups - get item group list
----------------------------

Get the list of item groups. Useful e.g. for custom interfaces.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/groups.req
    :response: http-examples/lmapi/groups.resp

Parameters:

* **k** valid API key
* **p** item type (must be set to lvar [LV])

.. _lmapi_increment:

increment - increment lvar value
--------------------------------

Increment value of a :ref:`logic variable<lvar>`. Initial value should be number

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/increment.req
    :response: http-examples/lmapi/increment.resp

Parameters:

* **k** valid API key
* **i** lvar id

.. _lmapi_reset:

reset - reset lvar state
------------------------

Set status and value of a :ref:`logic variable<lvar>` to *1*. Useful when lvar is being used as a timer to reset it, or as a flag to set it *True*.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/reset.req
    :response: http-examples/lmapi/reset.resp

Parameters:

* **k** valid API key
* **i** lvar id

.. _lmapi_set:

set - set lvar state
--------------------

Set status and value of a :ref:`logic variable<lvar>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/set.req
    :response: http-examples/lmapi/set.resp

Parameters:

* **k** valid API key
* **i** lvar id

Optionally:

* **s** lvar status
* **v** lvar value

.. _lmapi_state:

state - get lvar state
----------------------

State of lvar or all lvars can be obtained using state command.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/state.req
    :response: http-examples/lmapi/state.resp

Parameters:

* **k** valid API key

Optionally:

* **p** item type (none or lvar [LV])
* **i** item id
* **g** item group
* **full** return full state

.. _lmapi_state_history:

state_history - get item state history
--------------------------------------

State history of one :doc:`item</items>` or several items of the specified type can be obtained using **state_history** command.

If master key is used, method attempt to get stored state for item even if it currently doesn't present.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/state_history.req
    :response: http-examples/lmapi/state_history.resp

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

.. _lmapi_toggle:

toggle - toggle lvar state
--------------------------

switch value of a :ref:`logic variable<lvar>` between *0* and *1*. Useful when lvar is being used as a flag to switch it between *True*/*False*.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/toggle.req
    :response: http-examples/lmapi/toggle.resp

Parameters:

* **k** valid API key
* **i** lvar id


.. _lmapi_cat_lvar-management:

LVar management
===============



.. _lmapi_list:

list - list lvars
-----------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list.req
    :response: http-examples/lmapi/list.resp

Parameters:

* **k** API key with *master* permissions

Optionally:

* **g** filter by item group

Returns:

the list of all :ref:`lvars<lvar>` available

.. _lmapi_create_lvar:

create_lvar - create lvar
-------------------------

Create new :ref:`lvar<lvar>`

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/create_lvar.req
    :response: http-examples/lmapi/create_lvar.resp

Parameters:

* **k** API key with *master* permissions
* **i** lvar id

Optionally:

* **g** lvar group
* **save** save lvar configuration immediately

.. _lmapi_destroy_lvar:

destroy_lvar - delete lvar
--------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/destroy_lvar.req
    :response: http-examples/lmapi/destroy_lvar.resp

Parameters:

* **k** API key with *master* permissions
* **i** lvar id

.. _lmapi_get_config:

get_config - get lvar configuration
-----------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/get_config.req
    :response: http-examples/lmapi/get_config.resp

Parameters:

* **k** API key with *master* permissions
* **i** lvaar id

Returns:

complete :ref:`lvar<lvar>` configuration.

.. _lmapi_list_props:

list_props - list lvar properties
---------------------------------

Get all editable parameters of the :ref:`lvar<lvar>` confiugration.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_props.req
    :response: http-examples/lmapi/list_props.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id

.. _lmapi_save_config:

save_config - save lvar configuration
-------------------------------------

Saves :ref:`lvar<lvar>`. configuration on disk (even if it hasn't been changed)

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/save_config.req
    :response: http-examples/lmapi/save_config.resp

Parameters:

* **k** API key with *master* permissions
* **i** lvar id

.. _lmapi_set_prop:

set_prop - set lvar property
----------------------------

Set configuration parameters of the :ref:`lvar<lvar>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/set_prop.req
    :response: http-examples/lmapi/set_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call


.. _lmapi_cat_rule:

Decision matrix rules
=====================



.. _lmapi_create_rule:

create_rule - create new rule
-----------------------------

Creates new :doc:`decision rule<decision_matrix>`. Rule id (UUID) is generated automatically unless specified.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/create_rule.req
    :response: http-examples/lmapi/create_rule.resp

Parameters:

* **k** API key with *master* permissions

Optionally:

* **u** rule UUID to set
* **v** rule properties (dict)
* **save** save rule configuration immediately

.. _lmapi_destroy_rule:

destroy_rule - delete rule
--------------------------

Deletes :doc:`decision rule<decision_matrix>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/destroy_rule.req
    :response: http-examples/lmapi/destroy_rule.resp

Parameters:

* **k** API key with *master* permissions
* **i** rule id

.. _lmapi_get_rule:

get_rule - get rule information
-------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/get_rule.req
    :response: http-examples/lmapi/get_rule.resp

Parameters:

* **k** valid API key
* **i** rule id

.. _lmapi_list_rule_props:

list_rule_props - list rule properties
--------------------------------------

Get all editable parameters of the :doc:`decision rule</lm/decision_matrix>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_rule_props.req
    :response: http-examples/lmapi/list_rule_props.resp

Parameters:

* **k** valid API key
* **i** rule id

.. _lmapi_list_rules:

list_rules - get rules list
---------------------------

Get the list of all available :doc:`decision rules<decision_matrix>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_rules.req
    :response: http-examples/lmapi/list_rules.resp

Parameters:

* **k** valid API key

.. _lmapi_set_rule_prop:

set_rule_prop - set rule parameters
-----------------------------------

Set configuration parameters of the :doc:`decision rule</lm/decision_matrix>`.

.. note::

    Master key is required for batch set.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/set_rule_prop.req
    :response: http-examples/lmapi/set_rule_prop.resp

Parameters:

* **k** valid API key
* **i** rule id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call


.. _lmapi_cat_macro:

Logic control macros
====================



.. _lmapi_create_macro:

create_macro - create new macro
-------------------------------

Creates new :doc:`macro<macros>`. Macro code should be put in **xc/lm** manually.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/create_macro.req
    :response: http-examples/lmapi/create_macro.resp

Parameters:

* **k** API key with *master* permissions
* **i** macro id

Optionally:

* **g** macro group

.. _lmapi_destroy_macro:

destroy_macro - delete macro
----------------------------

Deletes :doc:`macro<macros>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/destroy_macro.req
    :response: http-examples/lmapi/destroy_macro.resp

Parameters:

* **k** API key with *master* permissions
* **i** macro id

.. _lmapi_get_macro:

get_macro - get macro information
---------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/get_macro.req
    :response: http-examples/lmapi/get_macro.resp

Parameters:

* **k** valid API key
* **i** macro id

.. _lmapi_groups_macro:

groups_macro - get macro groups list
------------------------------------

Get the list of macros. Useful e.g. for custom interfaces.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/groups_macro.req
    :response: http-examples/lmapi/groups_macro.resp

Parameters:

* **k** valid API key

.. _lmapi_list_macro_props:

list_macro_props - get macro configuration properties
-----------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_macro_props.req
    :response: http-examples/lmapi/list_macro_props.resp

Parameters:

* **k** API key with *master* permissions
* **i** macro id

.. _lmapi_list_macros:

list_macros - get macro list
----------------------------

Get the list of all available :doc:`macros<macros>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_macros.req
    :response: http-examples/lmapi/list_macros.resp

Parameters:

* **k** valid API key

Optionally:

* **g** filter by group

.. _lmapi_result:

result - macro execution result
-------------------------------

Get :doc:`macro<macros>` execution results either by action uuid or by macro id.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/result.req
    :response: http-examples/lmapi/result.resp

Parameters:

* **k** valid API key

Optionally:

* **u** action uuid or
* **i** macro id
* **g** filter by unit group
* **s** filter by action status: Q for queued, R for running, F for finished

Returns:

list or single serialized action object

.. _lmapi_run:

run - execute macro
-------------------

Execute a :doc:`macro<macros>` with the specified arguments.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/run.req
    :response: http-examples/lmapi/run.resp

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

.. _lmapi_set_macro_prop:

set_macro_prop - set macro configuration property
-------------------------------------------------

Set configuration parameters of the :doc:`macro<macros>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/set_macro_prop.req
    :response: http-examples/lmapi/set_macro_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call


.. _lmapi_cat_cycle:

Logic cycles
============



.. _lmapi_create_cycle:

create_cycle - create new cycle
-------------------------------

Creates new :doc:`cycle<cycles>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/create_cycle.req
    :response: http-examples/lmapi/create_cycle.resp

Parameters:

* **k** API key with *master* permissions
* **i** cycle id

Optionally:

* **g** cycle group

.. _lmapi_destroy_cycle:

destroy_cycle - delete cycle
----------------------------

Deletes :doc:`cycle<cycles>`. If cycle is running, it is stopped before deletion.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/destroy_cycle.req
    :response: http-examples/lmapi/destroy_cycle.resp

Parameters:

* **k** API key with *master* permissions
* **i** cycle id

.. _lmapi_get_cycle:

get_cycle - get cycle information
---------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/get_cycle.req
    :response: http-examples/lmapi/get_cycle.resp

Parameters:

* **k** valid API key
* **i** cycle id

Returns:

field "value" contains real average cycle interval

.. _lmapi_groups_cycle:

groups_cycle - get cycle groups list
------------------------------------

Get the list of cycles. Useful e.g. for custom interfaces.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/groups_cycle.req
    :response: http-examples/lmapi/groups_cycle.resp

Parameters:

* **k** valid API key

.. _lmapi_list_cycle_props:

list_cycle_props - get cycle configuration properties
-----------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_cycle_props.req
    :response: http-examples/lmapi/list_cycle_props.resp

Parameters:

* **k** API key with *master* permissions
* **i** cycle id

.. _lmapi_list_cycles:

list_cycles - get cycle list
----------------------------

Get the list of all available :doc:`cycles<cycles>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_cycles.req
    :response: http-examples/lmapi/list_cycles.resp

Parameters:

* **k** valid API key

Optionally:

* **g** filter by group

.. _lmapi_reset_cycle_stats:

reset_cycle_stats - reset cycle statistic
-----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/reset_cycle_stats.req
    :response: http-examples/lmapi/reset_cycle_stats.resp

Parameters:

* **k** valid API key
* **i** cycle id

.. _lmapi_set_cycle_prop:

set_cycle_prop - set cycle property
-----------------------------------

Set configuration parameters of the :doc:`cycle<cycles>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/set_cycle_prop.req
    :response: http-examples/lmapi/set_cycle_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** item id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call

.. _lmapi_start_cycle:

start_cycle - start cycle
-------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/start_cycle.req
    :response: http-examples/lmapi/start_cycle.resp

Parameters:

* **k** valid API key
* **i** cycle id

.. _lmapi_stop_cycle:

stop_cycle - stop cycle
-----------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/stop_cycle.req
    :response: http-examples/lmapi/stop_cycle.resp

Parameters:

* **k** valid API key
* **i** cycle id

Optionally:

* **wait** wait until cycle is stopped


.. _lmapi_cat_ext:

Macro extensions
================



.. _lmapi_get_ext:

get_ext - get loaded extension information
------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/get_ext.req
    :response: http-examples/lmapi/get_ext.resp

Parameters:

* **k** API key with *master* permissions
* **i** extension ID

.. _lmapi_list_ext:

list_ext - get list of available macro extensions
-------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_ext.req
    :response: http-examples/lmapi/list_ext.resp

Parameters:

* **k** API key with *master* permissions

Optionally:

* **full** get full information

.. _lmapi_list_ext_mods:

list_ext_mods - get list of available extension modules
-------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_ext_mods.req
    :response: http-examples/lmapi/list_ext_mods.resp

Parameters:

* **k** API key with *master* permissions

.. _lmapi_load_ext:

load_ext - load extension module
--------------------------------

Loads:doc:`macro extension</lm/ext>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/load_ext.req
    :response: http-examples/lmapi/load_ext.resp

Parameters:

* **k** API key with *master* permissions
* **i** extension ID
* **m** extension module

Optionally:

* **c** extension configuration
* **save** save extension configuration after successful call

.. _lmapi_modhelp_ext:

modhelp_ext - get extension usage help
--------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/modhelp_ext.req
    :response: http-examples/lmapi/modhelp_ext.resp

Parameters:

* **k** API key with *master* permissions
* **m** extension name (without *.py* extension)
* **c** help context (*cfg* or *functions*)

.. _lmapi_modinfo_ext:

modinfo_ext - get extension module info
---------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/modinfo_ext.req
    :response: http-examples/lmapi/modinfo_ext.resp

Parameters:

* **k** API key with *master* permissions
* **m** extension module name (without *.py* extension)

.. _lmapi_set_ext_prop:

set_ext_prop - set extension configuration property
---------------------------------------------------

appends property to extension configuration and reloads module

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/set_ext_prop.req
    :response: http-examples/lmapi/set_ext_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** extension id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call

.. _lmapi_unload_ext:

unload_ext - unload macro extension
-----------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/unload_ext.req
    :response: http-examples/lmapi/unload_ext.resp

Parameters:

* **k** API key with *master* permissions
* **i** extension ID


.. _lmapi_cat_remotes:

Remote controllers
==================



.. _lmapi_append_controller:

append_controller - connect remote UC via HTTP
----------------------------------------------

Connects remote :ref:`UC controller<lm_remote_uc>` to the local.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/append_controller.req
    :response: http-examples/lmapi/append_controller.resp

Parameters:

* **k** API key with *master* permissions
* **u** :doc:`/uc/uc_api` uri (*proto://host:port*, port not required if default)
* **a** remote controller API key (\$key to use local key)

Optionally:

* **m** ref:`MQTT notifier<mqtt_>` to exchange item states in real time (default: *eva_1*)
* **s** verify remote SSL certificate or pass invalid
* **t** timeout (seconds) for the remote controller API calls
* **save** save connected controller configuration on the disk immediately after creation

.. _lmapi_disable_controller:

disable_controller - disable connected controller
-------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/disable_controller.req
    :response: http-examples/lmapi/disable_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

Optionally:

* **save** save configuration after successful call

.. _lmapi_enable_controller:

enable_controller - enable connected controller
-----------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/enable_controller.req
    :response: http-examples/lmapi/enable_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

Optionally:

* **save** save configuration after successful call

.. _lmapi_get_controller:

get_controller - get connected controller information
-----------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/get_controller.req
    :response: http-examples/lmapi/get_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _lmapi_list_controller_props:

list_controller_props - get controller connection parameters
------------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_controller_props.req
    :response: http-examples/lmapi/list_controller_props.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _lmapi_list_controllers:

list_controllers - get controllers list
---------------------------------------

Get the list of all connected :ref:`UC controllers<lm_remote_uc>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_controllers.req
    :response: http-examples/lmapi/list_controllers.resp

Parameters:

* **k** API key with *master* permissions

.. _lmapi_list_remote:

list_remote - get a list of items from connected UCs
----------------------------------------------------

Get a list of the items loaded from the connected :ref:`UC controllers<lm_remote_uc>`. Useful to debug the controller connections.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_remote.req
    :response: http-examples/lmapi/list_remote.resp

Parameters:

* **k** API key with *master* permissions

Optionally:

* **i** controller id
* **g** filter by item group
* **p** filter by item type

.. _lmapi_reload_controller:

reload_controller - reload controller
-------------------------------------

Reloads items from connected UC

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/reload_controller.req
    :response: http-examples/lmapi/reload_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _lmapi_remove_controller:

remove_controller - disconnect controller
-----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/remove_controller.req
    :response: http-examples/lmapi/remove_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id

.. _lmapi_set_controller_prop:

set_controller_prop - set controller connection parameters
----------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/set_controller_prop.req
    :response: http-examples/lmapi/set_controller_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call

.. _lmapi_test_controller:

test_controller - test connection to remote controller
------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/test_controller.req
    :response: http-examples/lmapi/test_controller.resp

Parameters:

* **k** API key with *master* permissions
* **i** controller id


.. _lmapi_cat_job:

Scheduled jobs
==============



.. _lmapi_create_job:

create_job - create new job
---------------------------

Creates new :doc:`scheduled job<jobs>`. Job id (UUID) is generated automatically unless specified.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/create_job.req
    :response: http-examples/lmapi/create_job.resp

Parameters:

* **k** API key with *master* permissions

Optionally:

* **u** job UUID to set
* **v** job properties (dict)
* **save** save unit configuration immediately

.. _lmapi_destroy_job:

destroy_job - delete job
------------------------

Deletes :doc:`scheduled job<jobs>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/destroy_job.req
    :response: http-examples/lmapi/destroy_job.resp

Parameters:

* **k** API key with *master* permissions
* **i** job id

.. _lmapi_get_job:

get_job - get job information
-----------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/get_job.req
    :response: http-examples/lmapi/get_job.resp

Parameters:

* **k** API key with *master* permissions
* **i** job id

.. _lmapi_list_job_props:

list_job_props - list job properties
------------------------------------

Get all editable parameters of the :doc:`scheduled job</lm/jobs>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_job_props.req
    :response: http-examples/lmapi/list_job_props.resp

Parameters:

* **k** API key with *master* permissions
* **i** job id

.. _lmapi_list_jobs:

list_jobs - get jobs list
-------------------------

Get the list of all available :doc:`scheduled jobs<jobs>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/list_jobs.req
    :response: http-examples/lmapi/list_jobs.resp

Parameters:

* **k** API key with *master* permissions

.. _lmapi_set_job_prop:

set_job_prop - set job parameters
---------------------------------

Set configuration parameters of the :doc:`scheduled job</lm/jobs>`.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/lmapi/set_job_prop.req
    :response: http-examples/lmapi/set_job_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** job id
* **p** property name (or empty for batch set)

Optionally:

* **v** propery value (or dict for batch set)
* **save** save configuration after successful call

