LM API
======

:doc:`Logic Manager<lm>` LM API is called through URL request

**\http://<IP_address_LM:Port>/lm-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

All functions can be called using GET and POST methods. When POST method is
being used, the parameters can be passed to functions eitner as www-form or as
JSON.

.. note::

    Object creation and modification functions don't save configurations
    automatically unless you specify **save** parameter in API request. The
    system is designed to work in this way to let you discard the changes in
    case of the serious problems by killing the controller process.

    If you need to save any changes made without this parameter, restart the
    controller gracefully or use :doc:`/sys_api` **save** function.

.. contents::

.. _lm_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid :ref:`API KEY<lm_apikey>`

Parameters:

* **k** valid API key

Returns JSON dict with system info and current API key permissions (for
masterkey only  'master':true is returned)

.. code-block:: json

    {
        "acl": {
            "allow": {
                "cmd": true
            },
            "groups": [
                "system/#",
                "service",
                "security/+"
            ],
            "items": [],
            "key_id": "key1",
            "master": false,
            "sysfunc": false
        },
        "product_build": 2017082101,
        "product_code": "lm",
        "product_name": "EVA Logic Manager",
        "result": "OK",
        "system": "eva3-test1",
        "time": 1504489043.4566338,
        "version": "3.0.0"
    }

Errors:

* **403 Forbidden** the key has no access to the API

.. _lm_state:

state - get logic variable state
--------------------------------

State of the :ref:`lvar<lvar>` or all logic variables can be obtained using
**state** command.

Parameters:

* **k** valid API key
* **i** lvar ID
* **g** group filter, optional :ref:`mqtt<mqtt_>` masks can be used, for
  example group1/#, group1/+/lamps)
* **full=1** display extended item info, optional (config_changed, description,
  virtual, status_labels and action_enabled for unit)

Returns lvar status in JSON dict or array of dicts:

.. code-block:: json

    [
        {
            "expires": 0,
            "full_id": "service/test",
            "group": "service",
            "id": "test",
            "set_time": 1506345719.8540998,
            "status": 1,
            "type": "lvar",
            "value": "33"
        }
    ]

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist, or the key has no access to the lvar

set - set lvar state
--------------------

Allows to set status and value of a :ref:`logic variable<lvar>`.

Parameters:

* **k** valid API key
* **i** lvar id
* **s** lvar status, optional
* **v** lvar value, optional

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist, or the key has no access to the lvar

reset - reset lvar state
------------------------

Allows to set status and value of a :ref:`logic variable<lvar>` to *1*. Useful
when lvar is being used as a timer to reset it, or as a flag to set it *True*.

Parameters:

* **k** valid API key
* **i** lvar id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist, or the key has no access to the lvar

clear - clear lvar state
------------------------

Allows to set status (if **expires** lvar param > 0) or value (if **expires**
isn't set) of a :ref:`logic variable<lvar>` to *0*. Useful when lvar is being
used as a timer to stop it, or as a flag to set it *False*.

Parameters:

* **k** valid API key
* **i** lvar id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist, or the key has no access to the lvar

toggle - toggle lvar value
--------------------------

Allows to switch value of a :ref:`logic variable<lvar>` between *0* and *1*.
Useful when lvar is being used as a flag to switch it between *True*/*False*.

Parameters:

* **k** valid API key
* **i** lvar id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist, or the key has no access to the lvar

groups - get lvar groups list
-----------------------------
Get the list of the lvar groups. Useful i.e. for the custom interfaces.

Parameters:

* **k** valid API key

Returns JSON array:

.. code-block:: json

    [
        "parent_group1/group1",
        "parent_group1/group2"
    ]

Errors:

* **403 Forbidden** invalid API KEY

groups_macro - get macro groups list
------------------------------------
Get the list of the macro groups.

Parameters:

* **k** valid API key

Returns JSON array:

.. code-block:: json

    [
        "parent_group1/group1",
        "parent_group1/group2"
    ]

Errors:

* **403 Forbidden** invalid API KEY

list_macros - get macro list
----------------------------

Get the list of all available macros

Parameters:

* **k** valid API key
* **g** filter by group, optional (:ref:`MQTT<mqtt_>` masks may be used, i.e.
  group1/#, group1/+/service)

Returns JSON array:

.. code-block:: json

    [
        {
           "action_enabled": true,
           "description": "description",
           "full_id": "group/macro_id",
           "group": "group",
           "id": "macro_id",
           "oid": "lmacro:group/macro_id",
           "type": "lmacro"
        }
    ]

Errors:

* **403 Forbidden** invalid API KEY

run - execute macro
-------------------

Executes a :doc:`macro<macros>` with the specified arguments.

Parameters:

* **k** valid API key
* **i** macro id

optionally:

* **a** macro arguments, space separated
* **p** queue priority (less value - higher priority, default 100)
* **u** unique action ID (use this option only if you know what you do, the
  system assigns the unique ID by default)
* **w** the API request will wait for the completion of the action for the
  specified number of seconds
* **q** timeout (sec) for action processing in the public queue

Returns JSON dict with the following data (time** UNIX_TIMESTAMP):

.. code-block:: json

    {
       "err": "<compilation and exec errors>",
       "exitcode": exit_code,
       "item_group": "group",
       "item_id": "macro_id",
       "item_type": "lmacro",
       "out": "",
       "priority": priority,
       "status": "action_status",
       "time": {
           "created": creation_time,
           "pending": public_queue_pending_time,
           "queued": controller_queue_pending_time,
           "running": running_time
       },
       "uuid": "unique_action_id"
    }

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** macro doesn't exist, or the key has no access to the macro

In case the parameter w is not indicated or action is not finished in the
specified time, it should continue running, and its status may be checked in
accordance with assigned uuid. If action is terminated, exit code will stand
for the exit code of the macro. Additionally, "time" will be supplemented by
"completed", "failed" or "terminated". "Out" field contains the output of "out"
variable (if it was associated with a value in the macro), "err" field (in case
of macro compilation/execution errors)contains the error details.

result - macro execution result
-------------------------------



