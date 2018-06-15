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

.. _lm_set:

set - set lvar state
--------------------

Allows to set status and value of a :ref:`logic variable<lvar>`.

Parameters:

* **k** valid API key
* **i** lvar id
* **s** lvar status, optional
* **v** lvar value, optional

Returns JSON dict result="OK", if the state is set successfully.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist, or the key has no access to the lvar

.. _lm_reset:

reset - reset lvar state
------------------------

Allows to set status and value of a :ref:`logic variable<lvar>` to *1*. Useful
when lvar is being used as a timer to reset it, or as a flag to set it *True*.

Parameters:

* **k** valid API key
* **i** lvar id

Returns JSON dict result="OK", if the state is reset successfully.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist, or the key has no access to the lvar

.. _lm_clear:

clear - clear lvar state
------------------------

Allows to set status (if **expires** lvar param > 0) or value (if **expires**
isn't set) of a :ref:`logic variable<lvar>` to *0*. Useful when lvar is being
used as a timer to stop it, or as a flag to set it *False*.

Returns JSON dict result="OK", if the state is cleared successfully.

Parameters:

* **k** valid API key
* **i** lvar id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist, or the key has no access to the lvar

.. _lm_toggle:

toggle - toggle lvar value
--------------------------

Allows to switch value of a :ref:`logic variable<lvar>` between *0* and *1*.
Useful when lvar is being used as a flag to switch it between *True*/*False*.

Parameters:

* **k** valid API key
* **i** lvar id

Returns JSON dict result="OK", if the state is toggled successfully.

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

Get the list of all available :doc:`macros<macros>`.

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

.. _lm_run:

run - execute macro
-------------------

Executes a :doc:`macro<macros>` with the specified arguments.

Parameters:

* **k** valid API key
* **i** macro id

optionally:

* **a** macro arguments, space separated
* **p** queue priority (less value - higher priority, default 100)
* **u** unique action id (use this option only if you know what you do, the
  system assigns the unique ID by default)
* **w** the API request will wait for the completion of the action for the
  specified number of seconds
* **q** timeout (sec) for action processing in the public queue

Returns JSON dict with the following data (time** UNIX_TIMESTAMP):

.. code-block:: text

    {
       "err": "<compilation and exec errors>",
       "exitcode": <exit_code>,
       "item_group": "<group>",
       "item_id": "<macro_id>",
       "item_type": "lmacro",
       "out": "[macro out variable]",
       "priority": <priority>,
       "status": "<action status>",
       "time": {
           "created": <creation_time>,
           "pending": <public_queue_pending_time>,
           "queued": <controller_queue_pending_time>,
           "running": <running_time>
       },
       "uuid": "unique_action_id"
    }

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** macro doesn't exist, or the key has no access to the macro

In case the parameter **w** is not indicated or action is not finished in the
specified time, it should continue running, and its status may be checked in
accordance with assigned uuid. If action is terminated, exit code will stand
for the exit code of the macro. Additionally, **time** will be supplemented by
*completed*, *failed* or *terminated*. **out** field contains the output of
*out* variable (if it was associated with a value in the macro), **err** field
(in case of macro compilation/execution errors)contains the error details.

.. _lm_result:

result - macro execution result
-------------------------------

Get :doc:`macro<macros>` execution results either by action uuid or by macro id.

Parameters:

* **k** valid API key

optionally:

* **i** macro_id
* **u** action uuid (either action uuid or macro_id must be specified)
* **g** filter by macro group
* **s** filter by action status (Q - queued, R - running, F - finished)

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** macro or action doesn't exist, or the key has no access to
  the macro

Actions remain in the system until they receive the status *completed*,
*failed* or *terminated* and until **keep_action_status** time indicated in
:ref:`contoller configuration<lm_ini>` passes.

.. note::

    This function doesn't return results of the unit actions executed by macros

list - get list of all logic variables
--------------------------------------

Parameters:

* **k** masterkey API key
* **g** filter by group (optional)

Returns JSON array which contains :ref:`lvars<lvar>`:


.. code-block:: json

    [
        {
           "description": "description",
           "expires": 0,
           "full_id": "group/id",
           "group": "group",
           "id": "lvare_id",
           "oid": "lvar:group/id",
           "set_time": 9999999,
           "type": "lvar"
        }
    ]

Errors:

* **403 Forbidden** invalid API KEY

get_config - get logic variable configuration
---------------------------------------------

Parameters:

* **k** masterkey
* **i** lvar id

Returns complete :ref:`lvar<lvar>` configuration.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist

save_config - save lvar configuration on disk
---------------------------------------------

Saves lvar configuration on disk (even if it wasn't changed)

Parameters:

* **k** masterkey
* **i** lvar id

Returns JSON dict result="OK", if the configuration is saved successfully.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_list_props:

list_props - get editable lvar parameters
-----------------------------------------

Allows to get all editable parameters of the :ref:`lvar configuration<lvar>`.

Parameters:

* **k** masterkey
* **i** lvar id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** lvar doesn't exist

.. _lm_set_prop:

set_prop - set item parameters
------------------------------

Allows to set configuration parameters of the lvar.

Parameters:

* **k** masterkey
* **i** lvar id
* **p** lvar configuration param
* **v** param value

Returns result="OK if the parameter is set, or result="ERROR", if an error
occurs.

Errors:

* **403 Forbidden** invalid API KEY

create_lvar - create new lvar
-----------------------------

Creates new :ref:`lvar<lvar>`.

Parameters:

* **k** masterkey
* **i** lvar id
* **g** lvar group

optionally:

* **save=1** save lvar configuration on the disk immediately after creation

Returns result="OK if the lvar is created, or result="ERROR", if the error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

destroy_lvar - delete lvar
--------------------------

Deletes :ref:`lvar<lvar>`.

Parameters:

* **k** masterkey
* **i** lvar id

Returns result="OK if the lvar is deleted, or result="ERROR", if error
occurred.

LVar configuration may be immediately deleted from the disk, if there is
*db_update=instant* set in :ref:`controller configuration<lm_ini>`, at the
moment of the shutdown, if there is *db_update=on_exit*, or when
calling :doc:`/sys_api` save (or save in :doc:`LM EI<lm_ei>`), if there is
*db_update=manual*.

If configuration is not deleted by either of these, you should delete it
manually by removing the file runtime/lm_lvar.d/ID.json, otherwise the
lvar(s) will remain in the system after restarting the controller.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_list_macro_props:

list_macro_props - get editable macro parameters
------------------------------------------------

Allows to get all editable parameters of the :doc:`macro
configuration<macros>`.

Parameters:

* **k** masterkey
* **i** macro id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** macro doesn't exist

.. _lm_set_macro_prop:

set_macro_prop - set macro parameters
-------------------------------------

Allows to set configuration parameters of the macro.

Parameters:

* **k** masterkey
* **i** macro id
* **p** macro configuration param
* **v** param value

Returns result="OK if the parameter is set, or result="ERROR", if an error
occurs.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_create_macro:

create_macro - create new macro
-------------------------------

Creates new :doc:`macro<macros>`. Macro code should be put in **xc/lm**
manually.

Parameters:

* **k** masterkey
* **i** macro id
* **g** macro group

optionally:

* **save=1** save macro configuration on the disk immediately after creation

Returns result="OK if the macro is created, or result="ERROR", if the error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

destroy_macro - delete macro
----------------------------

Deletes :doc:`macro<macros>`.

Parameters:

* **k** masterkey
* **i** macro id

Returns result="OK if the macro is deleted, or result="ERROR", if error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

list_rules - get rules list
---------------------------

Get the list of all available :doc:`decision rules<decision_matrix>`.

Parameters:

* **k** valid API key

Returns JSON array of rules and their properties.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_list_rule_props:

list_rule_props - get editable rule parameters
-----------------------------------------------

Allows to get all editable parameters of the :doc:`decision
rule<decision_matrix>`.

Parameters:

* **k** masterkey or a key with *allow=dm_rule_props* to access
  **in_range_\***,_**enabled** and **chillout_time** rule props, or with an
  access to a certain rule by ID

* **i** rule id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** rule doesn't exist

.. _lm_set_rule_prop:

set_rule_prop - set rule parameters
-----------------------------------

Allows to set configuration parameters of the rule.

Parameters:

* **k** masterkey or a key with *allow=dm_rule_props* to access
  in_range,_\*enabled and **chillout_time** rule settings, or with an access to
  a certain rule
* **i** rule id
* **p** rule configuration param
* **v** param value

Returns result="OK if the parameter is set, or result="ERROR", if an error
occurs.

Errors:

* **403 Forbidden** invalid API KEY

create_rule - create new rule
------------------------------

Creates new :doc:`decision rule<decision_matrix>`. Rule id is always generated
automatically.

Parameters:

* **k** masterkey

optionally:

* **save=1** save rule configuration on the disk immediately after creation

Returns result="OK if the rule is created, or result="ERROR", if the error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

destroy_rule - delete rule
----------------------------

Deletes :doc:`decision rule<decision_matrix>`.

Parameters:

* **k** masterkey
* **i** rule id

Returns result="OK if the rule is deleted, or result="ERROR", if error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_list_remote:

list_remote - get a list of items from connected UCs
----------------------------------------------------

Get a list of the items loaded from the connected :ref:`UC
controllers<lm_remote_uc>`.  Useful to debug the controller connections.

Parameters:

* **k** masterkey

optionally:

* **g** item group
* **p** item type (*U* for :ref:`unit<unit>`, *S* for :ref:`sensor<sensor>`)

Returns the JSON array of :ref:`units<unit>` and :ref:`sensors<sensor>` loaded
from the remote controllers. Additional field **controller_id** is present in
any item indicating the controller it's loaded from.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_list_controllers:

list_controllers - get controllers list
---------------------------------------

Get the list of all connected :ref:`UC controllers<lm_remote_uc>`.

Parameters:

* **k** valid API key

Returns JSON array:

.. code-block:: json

    [
        {
        "description": "<controller_description>",
        "full_id": "<uc/controller_id>",
        "group": "uc",
        "id": "<controller_id>",
        "oid": "<remote_uc:uc/controller_id>",
        "type": "remote_uc"
        }
    ]

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_list_controller_props:

list_controller_props - get editable controller parameters
----------------------------------------------------------

Allows to get all editable parameters of the connected :ref:`UC
controller<lm_remote_uc>`.

* **k** masterkey
* **i** controller id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** controller doesn't exist

.. _lm_set_controller_prop:

set_controller_prop - set controller parameters
-----------------------------------------------

Allows to set configuration parameters of the connected UC.

Parameters:

* **k** masterkey
* **i** controller id
* **p** controller configuration param
* **v** param value

Returns result="OK if the parameter is set, or result="ERROR", if an error
occurs.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_append_controller:

append_controller - connect remote UC
-------------------------------------

Connects remote :ref:`UC controller<lm_remote_uc>` to the local.

Parameters:

* **k** masterkey
* **uri** :doc:`/uc/uc_api` uri (*proto://host:port*)
* **a** remote controller API key (\$key to use local key)

optionally:

* **m** :ref:`MQTT notifier<mqtt_>` to exchange item states in real time
* **s** *True*/*False* (*1*/*0*) verify remote SSL certificate or pass invalid
* **t** timeout (seconds) for the remote controller API calls
* **save=1** save connected controller configuration on the disk immediately
  after creation

Returns result="OK if the controller is connected, or result="ERROR", if the
error occurred.

The remote controller id is being obtained and set automatically according to
its hostname or **name** field in the controller configuration. The remote
controller id can't be changed.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_remove_controller:

remove_controller - disconnect UC
---------------------------------

Disconnects the remote :ref:`UC controller<lm_remote_uc>`.

Parameters:

* **k** masterkey
* **i** controller id

Returns result="OK if the controller is disconnected, or result="ERROR", if
error occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _lm_reload_controller:

reload_controller - reload items from UC
----------------------------------------

Allows to immediately reload all the :doc:`items</items>` and their status from
the remote :ref:`UC controller<lm_remote_uc>`.

Parameters:

* **k** masterkey
* **i** controller id

Returns result="OK if the controller is deleted, or result="ERROR", if error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. include:: ../userauth.rst

