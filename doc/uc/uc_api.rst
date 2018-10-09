UC API
******

:doc:`Universal Controller<uc>` UC API is called through URL request

**\http://<IP_address_UC:Port>/uc-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

All functions can be called using GET and POST methods. When POST method is
used, the parameters can be passed to functions either as www-form or as JSON.

.. note::

    Object creation and modification functions don't save configurations
    automatically unless you specify **save** parameter in API request. The
    system is designed to work this way to let you discard the changes in case
    of serious problems by killing the controller process.

    If you need to save any changes made without this parameter, restart the
    controller gracefully or use :doc:`/sys_api` **save** function.

.. contents::

.. _uc_test:

test - test API/key and get system info
=======================================

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
======================

State of the :doc:`item</items>` or all items of the specified type can be
obtained using **state** command.

Parameters:

* **k** valid API key
* **i** item ID
* **p** item type (short forms U for unit, S for sensor may be used)
* **g** group filter, optional :ref:`mqtt<mqtt_>` masks can be used, for
  example group1/#, group1/+/lamps)
* **full** if *1*, display extended item info, optional (config_changed,
  description, virtual, status_labels and action_enabled for unit)

Returns item state in JSON dict or array of dicts:

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

where status and value - current item state, nstatus and nvalue (for unit) -
expected status and value.  Current and new status and value are different in
case the action is executed for the unit at the moment. In all other cases,
they are the same.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, or the key has no access to the item

.. _uc_state_history:

state_history - get item state history
======================================

State history of one :doc:`item</items>` or several items of the specified type
can be obtained using **state_history** command.

Parameters:

* **k** valid API key
* **i** item ID, or multiple IDs, comma separated
* **a** :doc:`notifier</notifiers>` ID which keeps history for the specified
  item(s) (default: **db_1**)
* **s** time frame start, ISO or Unix timestamp
* **e** time frame end, optional (default: current time), ISO or Unix timestamp
* **l** limit history records (optional)
* **x** item property (**status** or **value**)
* **t** time format (**iso** or **raw** for Unix timestamp)
* **w** fill frame with the specified interval (e.g. *1T* - 1 minute, *2H* - 2
  hours etc.), optional
* **g** output format, **list** (default) or **dict**

Returns state history for the chosen item(s) in the specified format.

To get state history for the multiple items:

* **w** param is required
* **g** should be specified as **list**

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, the key has no access to the item, or
  the history database is not found

.. _uc_action:

action - unit control actions
=============================

Create unit control action and put it into the queue of the controller.

Parameters:

* **k** valid API key
* **i** unique unit id
* **s** new unit status
* **v** new unit value

optionally:

* **p** action priority in queue (the less value is** the higher
  priority is, default is 100)
* **u** unique action id (use this option only if you know what you do, the
  system assigns the unique id by default)
* **w** the API request will wait for the completion of the action for the
  specified number of seconds
* **q** timeout (sec) for action processing in the public queue

Returns JSON dict with the following data (time** UNIX_TIMESTAMP):

.. code-block:: text

    {
       "err": "<output_stderr>",
       "exitcode": <exit_code>,
       "item_group": "<group>",
       "item_id": "<unit_id>",
       "item_type": "unit",
       "nstatus": <new_status>,
       "nvalue": "<new_value>",
       "out": "<output_stdout>",
       "priority": <priority>,
       "status": "<action_status>",
       "time": {
           "created": <creation_time>,
           "pending": <public_queue_pending_time>,
           "queued": <unit_queue_pending_time>,
           "running": <running_time>
       },
       "uuid": "<unique_action_id>"
    }

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to the unit

In case the parameter **w** is not present or action is not terminated in the
specified wait time, it will continue running, and its status may be checked in
with assigned uuid. If the action is terminated, **out** and **err** will have
not null values and the process exit code will be available at **exitcode**.
Additionally, **time** will be supplemented by *completed*, *failed* or
*terminated*.

.. _uc_action_toggle:

action_toggle - simple unit control
===================================

Create unit control action to switch its status between 0 and 1. Useful for
simple units.

Parameters:

* **k** valid API key
* **i** unique unit id

optionally:

* **p** action priority in queue (the less value is** the higher
  priority is, default is 100)
* **u** unique action id (use this option only if you know what you do, the
  system assigns the unique id by default)
* **w** the API request will wait for the completion of the action for the
  specified number of seconds
* **q** timeout (sec) for action processing in the public queue

Returns and behavior:

Same as :ref:`action<uc_action>`

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, or the key has no access to the item

.. _uc_result:

result - get action status
==========================

Checks the result of the action by its UUID or returns the actions for the
specified unit.

Parameters:

* **k** valid API key
* **u** action UUID or
* **i** unit id

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
============================

Terminate action execution or cancel the action if it's still queued

Parameters:

* **k** valid API key
* **u** action UUID
* **i** item id, either item id or action UUID must be specified

Returns:

Returns JSON dict result="OK", if the action is terminated. If the action is
still queued, it will be canceled. result="ERROR" may occur if the action
termination is disabled in unit configuration.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item or action with the specified UUID doesn't exist (or
  already completed), or the key has no access to it

.. _uc_q_clean:

q_clean - clean up the action queue
===================================

Cancel all queued actions, keep the current action running

Parameters:

* **k** valid API key
* **i** unit id

Returns JSON dict result="OK", if the queue is cleaned.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_kill:

kill - clean up the queue and terminate the actions
===================================================

Apart from canceling all queued commands, this function also terminates the
current running action.

Parameters:

* **k** valid API key
* **i** unit id

Returns JSON dict result="OK", if the command completed successfully. If the
current action of the unit cannot be terminated by configuration, the notice
"pt" = "denied" will be returned additionally (even if there's no action
running)

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_disable_actions:

disable_actions - disable actions for the unit
==============================================

Disables unit to run and queue new actions.

Parameters:

* **k** valid API key
* **i** unit id

Returns JSON dict result="OK", if actions are disabled.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_enable_actions:

enable_actions - enable actions for the unit
============================================

Enables unit to run and queue new actions.

Parameters:

* **k** valid API key
* **i** unit id

Returns JSON dict result="OK", if actions are enabled.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** unit doesn't exist, or the key has no access to it

.. _uc_update:

update - set item status
========================

Updates the status and value of the :doc:`item</items>`. This is one of the
ways of passive state update, for example with the use of an external
controller. Calling without **s** and **v** params will force item to perform
passive update requesting its status from script or driver.

Parameters:

* **k** valid API key
* **i** item id
* **s** item status (integer, optional)
* **v** item value (optional)

Returns JSON dict result="OK", if the state is updated successfully.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, or the key has no access to it

.. _uc_groups:

groups - get item group list
============================

Get the list of item groups. Useful e.g. for custom interfaces.

Parameters:

* **k** valid API key
* **p** item type (*U* for :ref:`unit<unit>`, *S* for :ref:`sensor<sensor>`),
  required

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
====================

Returns the list of all items available

Parameters:

* **k** masterkey

optionally:

* **p** item type (*U* for :ref:`unit<unit>`, *S* for :ref:`sensor<sensor>`)
* **g** item group

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
===================================

Returns complete :doc:`item configuration</items>`

Parameters:

* **k** masterkey
* **i** item id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, or the key has no access to it

.. _uc_save_config:

save_config - save item configuration on disk
=============================================

Saves item configuration on disk (even if it hasn't been changed)

Parameters:

* **k** masterkey
* **i** item id

Returns JSON dict result="OK", if the configuration is saved successfully.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_list_props:

list_props - get editable item parameters
=========================================

Allows to get all editable parameters of the
:doc:`item configuration</items>`

Parameters:

* **k** masterkey
* **i** item id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** item doesn't exist, or the key has no access to it

.. _uc_set_prop:

set_prop - set item parameters
==============================

Allows to set configuration parameters of the item.

Parameters:

* **k** masterkey
* **i** item id
* **p** item configuration param
* **v** param value

Returns result="OK" if the parameter is set, or result="ERROR", if an error
occurs.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_create:

create - create new item
========================

Creates new :doc:`item</items>`.

Parameters:

* **k** masterkey
* **i** item OID (**type:group/id**)

optionally:

* **virtual=1** unit is created as :doc:`virtual</virtual>`
* **save=1** save unit configuration on disk immediately after creation

Returns result="OK" if the item is created, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_create_unit:

create_unit - create new unit
=============================

Creates new :ref:`unit<unit>`.

Parameters:

* **k** masterkey
* **i** unit id
* **g** unit group

optionally:

* **virtual=1** unit is created as :doc:`virtual</virtual>`
* **save=1** save unit configuration on disk immediately after creation

Returns result="OK" if the unit is created, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_create_sensor:

create_sensor - create new sensor
=================================

Creates new :ref:`sensor<sensor>`.

Parameters:

* **k** masterkey
* **i** sensor ID
* **g** sensor group

optionally:

* **virtual=1** sensor is created as :doc:`virtual</virtual>`
* **save=1** save sensor configuration on disk immediately after creation

Returns result="OK" if the sensor is created, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_create_mu:

create_mu - create multiupdate
==============================

Creates new :ref:`multiupdate<multiupdate>`.

Parameters:

* **k** masterkey
* **i** multiupdate ID
* **g** multiupdate group

optionally:

* **virtual=1** multiupdate is created as :doc:`virtual</virtual>`
* **save=1** save multiupdate configuration on disk immediately after
  creation

Returns result="OK" if the multiupdate is created, or result="ERROR", if an
error occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_clone:

clone - clone item
==================

Creates a copy of the :doc:`item</items>`.

Parameters:

* **k** masterkey
* **i** item ID
* **n** new item ID
* **g** group for the new item

optionally:

* **save=1** save item configuration on disk immediately after creation

Returns result="OK" if the item is cloned, or result="ERROR", if an error
occurred.

.. note::

    Multiupdates can not be cloned

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_clone_group:

clone_group - clone all items in the group
==========================================

Creates a copy of all items from the group.

Parameters:

* **k** masterkey
* **g** group to clone
* **n** new group to clone to
* **p** item ID prefix, i.e. device1. for device1.temp1, device1.fan1 
* **r** iem ID prefix in the new group, i.e. device2

optionally:

* **save=1** save cloned items configurations on disk immediately after
  creation.

Returns result="OK" if the items were cloned, or result="ERROR", if an error
occurred. Only items with type unit and sensor are cloned.

Errors:

* **403 Forbidden** invalid API KEY

.. _uc_destroy:

destroy - delete item or group
==============================

Deletes the :doc:`item</items>` or the group (and all the items in it) from the
system.

Parameters:

* **k** masterkey
* **i** item id
* **g** item group (either id or group must be specified)

Returns result="OK" if the item/group is deleted, or result="ERROR", if an
error occurred.

Item configuration may be immediately deleted from the disk, if there is
*db_update=instant* set in :ref:`controller configuration<uc_ini>`, at the
moment of shutdown, if there is *db_update=on_exit*, or when calling
:doc:`/sys_api` save (or save in :doc:`UC EI<uc_ei>`), if there is
*db_update=manual*.

If configuration is not deleted by either of these, you should delete it
manually by removing the file runtime/uc_<type>.d/ID.json, otherwise the
item(s) will remain in the system after restarting the controller.

Errors:

* **403 Forbidden** invalid API KEY

.. _create_device:

create_device - create device items
===================================

Creates the :ref:`device<device>` from the specified template.

Parameters:

* **k** key with *allow=device* permissions
* **c** device config (*var=value*, comma separated or JSON dict)
* **t** device template (*runtime/tpl/TEMPLATE.json*, without *.json*
  extension)

optionally:

* **save=1** save items configuration on disk immediately after operation

Returns result="OK" if the item/group is deleted, or result="ERROR", if an
error occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _update_device:

update_device - update device items
===================================

Works similarly to :ref:`create_device` function but doesn't create new items,
updating the item configuration of the existing ones.

Parameters:

* **k** key with *allow=device* permissions
* **c** device config (*var=value*, comma separated or JSON dict)
* **t** device template (*runtime/tpl/TEMPLATE.json*, without *.json*
  extension)

optionally:

* **save=1** save items configuration on disk immediately after operation

Returns result="OK" if the item/group is deleted, or result="ERROR", if an
error occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _destroy_device:

destroy_device - destroy device items
=====================================

Works in an opposite way to :ref:`create_device` function, destroying all items
specified in the template.

Parameters:

* **k** key with *allow=device* permissions
* **c** device config (*var=value*, comma separated or JSON dict)
* **t** device template (*runtime/tpl/TEMPLATE.json*, without *.json*
  extension)

Returns result="OK" if the item/group is deleted, or result="ERROR", if an
error occurred.

Errors:

* **403 Forbidden** invalid API KEY

list_modbus_ports - list virtual ModBus ports
=============================================

Returns a list which contains all virtual ModBus ports.

Parameters:

* **k** masterkey

Errors:

* **403 Forbidden** invalid API KEY

create_modbus_port - create virtual ModBus port
===============================================

Creates virtual :doc:`ModBus port</modbus>` with the specified configuration.

Parameters:

* **k** masterkey
* **i** virtual port ID which will be used later in :doc:`PHI</drivers>`
  configurations, required
* **p** ModBus params, required
* **l=1** lock port on operations, which means to wait while ModBus port is
  used by other controller thread (driver command)
* **t** ModBus operations timeout (in seconds, default: default timeout)
* **r** retry attempts for each operation (default: no retries)
* **d** delay between virtual port operations (default: 20ms)

Optionally:

* **save=1** save ModBus port config after creation

ModBus params should contain the configuration of hardware ModBus port. The
following hardware port types are supported:

* **tcp** , **udp** ModBus protocol implementations for TCP/IP networks. The
  params should be specified as: *<protocol>:<host>[:port]*, e.g.
  *tcp:192.168.11.11:502*

* **rtu**, **ascii**, **binary** ModBus protocol implementations for the local
  bus connected with USB or serial port. The params should be specified as:
  *<protocol>:<device>:<speed>:<data>:<parity>:<stop>* e.g.
  *rtu:/dev/ttyS0:9600:8:E:1*

Returns result="OK" if port is created, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

test_modbus_port - verifies virtual ModBus port
===============================================

Verifies virtual :doc:`ModBus port</modbus>` by calling connect() ModBus client
method.

Parameters:

* **k** masterkey
* **i** virtual port ID

.. note::

    As ModBus UDP doesn't require a port to be connected, API call always
    returns "OK" result.

Returns result="OK" if port test is passed, or result="ERROR", if an error
occurred.

destroy_modbus_port - delete virtual ModBus port
================================================

Deletes virtual :doc:`ModBus port</modbus>`.

Parameters:

* **k** masterkey
* **i** virtual port ID

Returns result="OK" if port is deleted, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

list_phi - list loaded PHIs
===========================

Returns a list which contains all loaded :doc:`Physical Interfaces</drivers>`.

Parameters:

* **k** masterkey

Errors:

* **403 Forbidden** invalid API KEY

load_phi - load PHI
===================

Loads :doc:`Physical Interface</drivers>`.

Parameters:

* **k** masterkey
* **i** PHI ID, required
* **m** PHI module, required
* **c** PHI configuration

Optionally:

* **save=1** save driver configuration after successful call

Returns a dict with information about PHI if module is loaded, or
result="ERROR", if an error occurred.

.. note::

    After successful load PHI automatically creates a :doc:`driver</drivers>`
    with ID <PHI_ID>.default

Errors:

* **403 Forbidden** invalid API KEY

unload_phi - unload PHI 
=======================

Unloads PHI. PHI should not be used by any :doc:`driver</drivers>` (except
*default*, but the driver should not be in use by any :doc:`item</items>`).

Parameters:

* **k** masterkey
* **i** PHI ID

Returns result="OK" if module is unloaded, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

put_phi_mod - upload PHI module
===============================

Allows to upload new PHI module to *xc/drivers/phi* folder.

Parameters:

* **k** masterkey
* **m** PHI module name (without *.py* extension)
* **c** PHI module content (as-is)

Optionally:

* **force==1** overwrite PHI module file if exists

Returns result="OK" if module is uploaded, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

unlink_phi_mod - delete PHI module file
=======================================

Deletes PHI module file, if the module is loaded, all its instances should be
unloaded first.

Parameters:

* **k** masterkey
* **m** PHI module name (without *.py* extension)

Returns result="OK" if module is deleted, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

get_phi - get loaded PHI information
====================================

Returns a dict with information about PHI

Parameters:

* **k** masterkey
* **i** PHI ID

Errors:

* **403 Forbidden** invalid API KEY
* **404 Forbidden** PHI not found
* **500 Internal Error** inaccessible PHI

test_phi - test PHI
===================

Returns PHI test result. All PHIs respond to **self** command, **help** command
returns all available test commands.

Parameters:

* **k** masterkey
* **i** PHI ID
* **c** test command

Returns test result. *self* command always returns a JSON string (not a dict),
either *OK* or *FAILED*.

Errors:

* **403 Forbidden** invalid API KEY
* **404 Forbidden** PHI not found
* **500 Internal Error** inaccessible PHI or PHI test is failed

exec_phi - execute additional PHI commands
==========================================

Returns PHI command execution result. **help** command returns all available
commands.

Parameters:

* **k** masterkey
* **i** PHI ID
* **c** command to exec

Returns command execution result (usually strings *OK*, *FAILED* or *not
implemented*)

Errors:

* **403 Forbidden** invalid API KEY
* **404 Forbidden** PHI not found
* **500 Internal Error** inaccessible PHI or PHI test is failed

list_phi_mods - get list of available PHI modules
=================================================

Returns a list of all available PHI modules.

Parameters:

* **k** masterkey

Errors:

* **403 Forbidden** invalid API KEY

modinfo_phi - get PHI module info
=================================

Returns a dict with information about PHI module.

Parameters:

* **k** masterkey
* **m** PHI module

Errors:

* **403 Forbidden** invalid API KEY
* **500 Internal Error** inaccessible PHI module

modhelp_phi - get PHI module usage help
=======================================

Returns a dict with PHI usage help.

Parameters:

* **k** masterkey
* **m** PHI module
* **c** help context (*cfg*, *get* or *set*)

Errors:

* **403 Forbidden** invalid API KEY
* **500 Internal Error** inaccessible PHI module

list_drivers - list loaded drivers
==================================

Returns a list of loaded :doc:`drivers</drivers>`

Parameters:

* **k** masterkey

Errors:

* **403 Forbidden** invalid API KEY

load_driver - load driver
=========================

Loads a :doc:`driver</drivers>`, combining previously loaded PHI and chosen LPI
module.

Parameters:

* **k** masterkey
* **i** LPI ID
* **m** LPI module
* **p** PHI ID
* **c** Driver (LPI) configuration, optional

Optionally:

* **save=1** save driver configuration after successful call

.. note::

    Driver ID is a combination of PHI and LPI IDs: DRIVER_ID = PHI_ID.LPI_ID

Returns result="OK" if driver is loaded, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

get_driver - get loaded driver information
==========================================

Parameters:

* **k** masterkey
* **i** PHI ID

Returns a dict with information about driver (both LPI and PHI)

Errors:

* **403 Forbidden** invalid API KEY
* **500 Internal Error** inaccessible driver

unload driver - unload driver
=============================

Unloads specified driver (LPI only, leaving PHI untouched)

Parameters:

* **k** masterkey
* **i** Driver ID

Returns result="OK" if driver is unloaded, or result="ERROR", if an error
occurred.

Errors:

* **403 Forbidden** invalid API KEY

list_lpi_mods - get list of available LPI modules
=================================================

Returns a list of all available LPI modules.

Parameters:

* **k** masterkey

Errors:

* **403 Forbidden** invalid API KEY

modinfo_lpi - get LPI module info
=================================

Returns a dict with information about LPI module.

Parameters:

* **k** masterkey
* **m** LPI module

Errors:

* **403 Forbidden** invalid API KEY
* **500 Internal Error** inaccessible LPI module

modhelp_lpi - get LPI module usage help
=======================================

Returns a dict with LPI usage help.

Parameters:

* **k** masterkey
* **m** LPI module
* **c** help context (*cfg*, *action* or *update*)

Errors:

* **403 Forbidden** invalid API KEY
* **500 Internal Error** inaccessible LPI module

set_driver - set driver to item
===============================

Sets the specified driver to :doc:`item</items>`, automatically updating item
props:

* **action_driver_config**, **update_driver_config** to the specified
  configuration
* **action_exec**, **update_exec** to do all operations via driver function
  calls (sets both to *|<driver_id>*)

Parameters:

* **k** masterkey
* **i** item ID
* **d** driver ID (if none - all above item props are set to *null*)
* **c** configuration (e.g. port number)

Optionally:

* **save=1** save item configuration after successful call

Returns result="OK" if driver is set, or result="ERROR", if an error occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. include:: ../userauth.rst
.. include:: ../common_reserved_funcs.rst

.. _uc_udp_api:

UDP API
=======

UDP API enables to call API action and update functions by sending a simple UDP
packet.

Basics
------

As there is no feedback in UDP, it is not recommended to use UDP API in cases
where reliability is critical, but its usability for programmable
microcontrollers sometimes takes advantage.

To update the status of the item send the following UDP packet to API port:

    <ID> u <status> [value]

(**ID** - item id, **value** - optional parameter).

To send :ref:`action<uc_action>` for the unit send the following UDP packet to
API port:

    <ID> <status> [value] [priority]

(value and priority** optional parameters).

If you needs to skip the parameter, set it to 'None'. For example:

    sensor1 u None 29.55

will keep sensor1 status and set value 29.55;

or

    unit1 1 None 50

will run the action for unit1 for changing its status to 1, without changing
the value, with priority 50.

Batch commands
--------------

You can specify multiple commands in one packet separating them with NL (*\n*)
symbol. Example::

    sensor1 u 1 29.55
    sensor2 u 1 26
    sensor3 u 1 38

Encryption and authentication
-----------------------------

You may specify in :ref:`controller configuration<uc_ini>` to accept only
encrypted packets from the specified hosts or networks. By default it's
recommended to accept unencrypted packets without authentication only in
trusted networks. The packet is encrypted and signed with API key and can not
be decrypted and used without having it, so API key acts both for encryption
and authentication.

Encrypted packet format is:

    \|KEY_ID\|ENCRYPTED_DATA

Where **KEY_ID** is API key ID and **ENCRYPTED_DATA** - UDP API packet (which
may contain either single or multiple commands at once). The data is encrypted
using `Fernet <https://cryptography.io/en/latest/fernet/>`_ - a symmetric
encryption method which uses 128-bit AES in CBC mode and PKCS7
padding, with HMAC using SHA256 for authentication.

Fernet requires 32-bit base64-encoded key, so before data encryption, API key
should be converted with the following: base64encode(sha256sum(api_key)).

Python example:

.. code-block:: python

    import hashlib
    import base64

    from cryptography.fernet import Fernet

    api_key = 'mysecretapikey'
    data = 'sensor1 u 1 29.55'

    encryption_key = base64.b64encode(hashlib.sha256(api_key.encode()).digest())
    ce = Fernet(encryption_key)

    result = ce.encrypt(data.encode())

Fernet implementation is simple and pre-made libraries are available for all
major programming languages.
