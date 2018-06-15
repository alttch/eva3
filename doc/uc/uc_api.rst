UC API
======

:doc:`Universal Controller<uc>` UC API is called through URL request

**\http://<IP_address_UC:Port>/uc-api/function**

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

.. _uc_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid :ref:`API KEY<uc_apikey>`

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
                "room1/#",
                "windows",
                "hall/+"
            ],
            "items": [],
            "key_id": "key1",
            "master": false,
            "sysfunc": false
        },
        "product_build": 2017082101,
        "product_code": "uc",
        "product_name": "EVA Universal Controller",
        "result": "OK",
        "system": "eva3-test1",
        "time": 1504489043.4566338,
        "version": "3.0.0"
    }

Errors:

* **403 Forbidden** the key has no access to the API

.. _uc_state:

state - get item state
----------------------

State of the :doc:`item</items>` or all items of the specified type can be
obtained using **state** command.

Parameters:

* **k** valid API key
* **i** item ID
* **p** item type (short forms U for unit, S for sensor may be used)
* **g** group filter, optional :ref:`mqtt<mqtt_>` masks can be used, for
  example group1/#, group1/+/lamps)
* **f** if *1*, display extended item info, optional (config_changed,
  description, virtual, status_labels and action_enabled for unit)

Returns item status in JSON dict or array of dicts:

.. code-block:: json

    [
        {
            "action_enabled": true,
            "full_id": "hall/lamps/lamp1",
            "group": "hall/lamps",
            "id": "lamp1",
            "nstatus": 1,
            "nvalue": "",
            "oid": "unit:hall/lamps/lamp1",
            "status": 1,
            "type": "unit",
            "value": ""
        }
    ]

where status and value** current item state, nstatus and nvalue (for unit) -
expected status and value.  Current and new status and value are different in
case the action is executed for the unit at the moment. In all other cases,
they are the same.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, or the key has no access to the item

.. _uc_action:

action - unit control actions
-----------------------------

Create unit control action and put it into the queue of the controller.

Parameters:

* **k** valid API key
* **ID** unique unit ID
* **s** new unit status
* **v** new unit value

optionally:

* **p** action priority in queue (the less value is** the higher
  priority is, default is 100)
* **u** unique action ID (use this option only if you know what you do, the
  system assigns the unique ID by default)
* **w** the API request will wait for the completion of the action for the
  specified number of seconds
* **q** timeout (sec) for action processing in the public queue

Returns JSON dict with the following data (time** UNIX_TIMESTAMP):

.. code-block:: json

    {
       "err": "output_stderr",
       "exitcode": exit_code,
       "item_group": "group",
       "item_id": "unit_id",
       "item_type": "unit",
       "nstatus": new_status,
       "nvalue": "new_value",
       "out": "output_stdout",
       "priority": priority,
       "status": "action_status",
       "time": {
           "created": creation_time,
           "pending": public_queue_pending_time,
           "queued": unit_queue_pending_time,
           "running": running_time
       },
       "uuid": "unique_action_id"
    }

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, or the key has no access to the item

In case the parameter 'w' is not present or action is not terminated in the
specified wait time, it will continue running, and it's status may be checked
in with assigned uuid. If the action is terminated, out and err will have not
null values and the process exit code will be available at 'exitcode'.
Additionally, 'time' will be appended by "completed", "failed" or "terminated".

.. _uc_action_toggle:

action_toggle - simple unit control
-----------------------------------

Create unit control action to switch it's status between 0 and 1. Useful for the
simple units.

Parameters:

* **k** valid API key
* **id** unique unit ID

optionally:

* **p** action priority in queue (the less value is** the higher
  priority is, default is 100)
* **u** unique action ID (use this option only if you know what you do, the
  system assigns the unique ID by default)
* **w** the API request will wait for the completion of the action for the
  specified number of seconds
* **q** timeout (sec) for action processing in the public queue

Returns and behaviour:

Same as :ref:`action<uc_action>`

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, or the key has no access to the item

.. _uc_result:

result - get action status
--------------------------

Checks the result of the action by it's UUID or returns the actions for the
specified unit.

Parameters:

* **k** valid API key
* **u** action UUID or
* **i** unit ID

Additionally results may be filtered by:

* **g** unit group
* **s** action status (*Q* queued, *R* running, *F* finished)

Returns:

Same JSON dict as :ref:`action<uc_action>`

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, action with the specified UUID doesn't
  exist, or the key has no access to them

.. _uc_terminate:

terminate - terminate action
----------------------------

Terminate action execution or cancel the action if it's still queued

Parameters:

* **k** valid API key
* **u** action UUID

Returns:

Returns JSON dict result="OK", if the action is terminated. If the action is
still queued, it will be canceled. result="ERROR" may occur if the action
termination is disabled in unit configuration.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** action with the specified UUID doesn't exist (or already
  compelted), or the key has no access to it

.. _uc_q_clean:

q_clean - clean up the action queue
-----------------------------------

Cancel all queued actions, keep the current action running

Parameters:

* **k** valid API key
* **i** unit ID

Returns JSON dict result="OK", if queue is cleaned.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_kill:

kill - clean up the queue and terminate the actions
---------------------------------------------------

Apart from canceling all queued commands, this function also terminates the
current running action.

Parameters:

* **k** valid API key
* **i** unit ID

Returns JSON dict result="OK", if the command completed successfully. If the
current action of the unit cannot be terminated by configuration, the notice
"pt" = "denied" will be returned additionally (even if there's no action
running)

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_disable_actions:

disable_actions - disable actions for the unit
----------------------------------------------

Disables unit to run and queue new actions.

Parameters:

* **k** valid API key
* **i** unit ID

Returns JSON dict result="OK", if actions are disabled.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_enable_actions:

enable_actions - enable actions for the unit
--------------------------------------------

Enables unit to run and queue new actions.

Parameters:

* **k** valid API key
* **i** unit ID

Returns JSON dict result="OK", if actions are enabled.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_update:

update - set item status
------------------------

Updates the status and value of the :doc:`item</items>`. This is one of the ways
of the passive state update, for example with the use of the external controller

Parameters:

* **k** valid API key
* **i** unit ID
* **s** unit status (integer, optional)
* **v** unit value (optional)

Returns JSON dict result="OK", if the state was updated successfully.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_groups:

groups - get item group list
----------------------------

Get the list of the item groups. Useful i.e. for the custom interfaces.

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

.. _uc_list:

list - get item list
--------------------

Returns the list of all items available

Parameters:

* **k** masterkey

Returns JSON array:

.. code-block:: json

    [
        {
            "description": "",
            "full_id": "item_group/item_id",
            "group": "item_group",
            "id": "item_id",
            "oid": "item_type:item_group/item_id",
            "type": "item_type"
        }
    
Errors:

* **403 Forbidden** invalid API KEY


.. _uc_get_config:

get_config - get item configuration
-----------------------------------

Returns complete :doc:`item configuration</items>`

Parameters:

* **k** masterkey

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_save_config:

save_config - save item configuration on disk
---------------------------------------------

Saves item configuration on disk (even if it wasn't changed)

Parameters:

* **k** masterkey
* **i** unit ID

Returns JSON dict result="OK", if the configuration was saved successfully.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_list_props:

list_props - get editable item parameters
-----------------------------------------

Allows to get all editable parameters of the
:doc:`item configuration</items>`

Parameters:

* **k** masterkey
* **i** unit ID

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_set_prop:

set_prop - set item parameters
------------------------------

Allows to set configuration parameters of the item.

Parameters:

* **k** masterkey
* **i** unit ID
* **p** item configuration param
* **v** param value

Returns result="OK if the parameter is set, or result="ERROR", if an error
occurs.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_create_unit:

create_unit - create new unit
-----------------------------

Creates new :ref:`unit<unit>`.

Parameters:

* **k** masterkey
* **i** unit ID
* **g** unit group

optionally:

* **virtual=1** unit is created as :doc:`virtual</virtual>`
* **save=1** save unit configuration on the disk immediately after creation

Returns result="OK if the unit was created, or result="ERROR", if the error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_create_sensor:

create_sensor - create new sensor
---------------------------------

Creates new :ref:`sensor<sensor>`.

Parameters:

* **k** masterkey
* **i** sensor ID
* **g** sensor group

optionally:

* **virtual=1** sensor is created as :doc:`virtual</virtual>`
* **save=1** save sensor configuration on the disk immediately after creation

Returns result="OK if the sensor was created, or result="ERROR", if the error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_create_mu:

create_mu - create multiupdate
------------------------------

Creates new :ref:`multiupdate<multiupdate>`.

Parameters:

* **k** masterkey
* **i** multiupdate ID
* **g** multiupdate group

optionally:

* **virtual=1** multiupdate is created as :doc:`virtual</virtual>`
* **save=1** save multiupdate configuration on the disk immediately after
  creation

Returns result="OK if the multiupdate was created, or result="ERROR", if the
error occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_clone:

clone - clone item
------------------

Creates a copy of the :doc:`item</items>`.

Parameters:

* **k** masterkey
* **i** item ID
* **n** new item ID
* **g** group for the new item

optionally:

* **save=1** save item configuration on the disk immediately after creation

Returns result="OK if the item was loned, or result="ERROR", if the error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_clone_group:

clone_group - clone all items in the group
------------------------------------------

Creates a copy of the all items from the group.

Parameters:

* **k** masterkey
* **g** group to clone
* **n** new group to clone to
* **p** item ID prefix, i.e. device1. for device1.temp1, device1.fan1 
* **r** iem ID prefix in the new group, i.e. device2

optionally:

* **save=1** save cloned items configurations on the disk immediately after
  creation.

Returns result="OK if the items were cloned, or result="ERROR", if error
occurred. Only items with type unit and sensor are cloned.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_destroy:

destroy - delete item or group
------------------------------

Deletes the item or the group (and all the items in it) from the system.

Returns result="OK if the item/group was deleted, or result="ERROR", if error
occurred.

Item configuration may be immediately deleted from the disk, if there is
db_update=instant set in server configuration, at the moment server's work is
completed, if there is db_update=on_exit, or when calling :doc:`/sys_api` save
(or save in :doc:`UC EI<uc_ei>`), if there is db_update=manual.

If configuration is not deleted by either of these, you should delete it
manually by removing the file runtime/uc_<type>.d/ID.json, otherwise the
item(s) will remain in the system after
restarting the server.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc-users:

User authorization using login/password
---------------------------------------

Third-party apps may authorize :doc:`users</sys_api>` using login and password
as an alternative for authorization via API key.

.. _uc-login:

login - user authorization
~~~~~~~~~~~~~~~~~~~~~~~~~~

Authorizes user in the system and and opens up a new authorized session.
Session ID is stored in cookie.

Attention! Session is created for all requests to API, even if login is not
used; web-browsers use the same session for the host even if apps are running
on different ports. Therefore, when you use web-apps (even if you use the same
the same browser to simultaneously assess system interfaces or other apps) each
app/interface should be associated with different domains/alias/different host
IP addresses.

Parameters:

* **u** user name
* **p** user password

Returns JSON dict { "result" "OK", "key": "APIKEY_ID" }, if the user is
authorized.

Errors:

* **403 Forbidden** invalid user name / password

.. _uc-logout:

logout
~~~~~~

Finishes the authorized session

Parameters: none

Returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** no session available / session is already finished

.. _uc_udp_api:

UDP API
-------

UDP API enables to call API action and update functions by sending a simple UDP
packets.

As there is no feedback in UDP, it is not recommended to use UDP API in cases
where reliability is cricial, but its usability for programmable
microcontrollers sometimes takes advantage.

To update the status of the item send the following UDP packet to API port:

    ID u <status> [value]

(ID** item ID, value** optional parameter).

To send :ref:`action<uc_action>` for the unit send the following UDP packet to
API port:

    ID <status> [value] [priority]

(value and priority** optional parameters).


If you needs to skip the parameter, set it to 'None'. For example:

    sensor1 u None 29.55

will keep sensor1 status and set value 29.55

or

    unit1 1 None 50

will run the action for unit1 for changing it's status to 1, without changing
the value, with priority 50.
