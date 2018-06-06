UC API
======

:doc:`Universal Controller<uc>` UC API is called through URL request

*\http://<IP_address_UC:Port>/uc-api/function?parameters*

If SSL is allowed in the controller configuration file, you can also use https
calls.

All functions can be called using GET and POST methods.

.. _test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid API KEY

Parameters:

* k - valid API key

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

* 403 Forbidden if the key has no access to the API.

.. _state:

state - get item state
----------------------

Status of the :doc:`item</items>` or all items of the specified type can be
obtained using *state* command.

Parameters:

* k - valid API key
* i=ID - item ID
* p=TYPE - item type (short forms U for unit, S for sensor may be used)
* g - group filter, optional :doc:`mqtt</notifiers>` masks can be used, for
  example group1/#, group1/+/lamps)
* full=1 - display extended item info, optional (config_changed, description,
  virtual, status_labels and action_enabled for unit)

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

where status and value - current item state, nstatus and nvalue (for unit) -
expected status and value.  Current and new status and value are different in
case the action is executed for the unit at the moment. In all other cases,
they are the same.

Errors:

* 403 Forbidden - invalid API KEY
* 404 Not Found - item doesn't exist, or the key has no access to the item

.. _action:

action - send unit control action
---------------------------------

Create unit control action and put it into the queue of the controller.

Parameters:

* k - valid API key
* ID - unique unit ID
* s - new unit status
* v - new unit value

optionally:

* p=PRIORITY - action priority in queue (the less value is - the higher priority
  is, default is 100)
* u=UUID - unique action ID (use this option only if you know what you do, the
  system assigns the unique ID by default)
* w=sec - the API request will wait for the completion of the action for the
  specified number of seconds
* q=sec - timeout for action processing in the public queue

Returns JSON dict with the following data (time - UNIX_TIMESTAMP):

.. code-block:: json

    {
       "err": "OUTPUT_STDERR",
       "exitcode": EXIT_CODE,
       "item_group": "GROUP",
       "item_id": "UNIT_ID",
       "item_type": "unit",
       "nstatus": NEW_STATUS,
       "nvalue": "NEW_VALUE",
       "out": "OUTPUT_STDOUT",
       "priority": PRIORITY,
       "status": "ACTION_STATUS",
       "time": {
           "created": CREATION_TIME,
           "pending": PUBLIC_QUEUE_PENDING_TIME,
           "queued": UNIT_QUEUE_PENDING_TIME,
           "running": RUNNING_TIME
       },
       "uuid": "UNIQUE_ACTION_ID"
    }

Errors:

* 403 Forbidden - invalid API KEY
* 404 Not Found - item doesn't exist, or the key has no access to the item

In case the parameter 'w' is not present or action is not terminated in the
specified wait time, it will continue running, and it's status may be checked
in with assigned uuid. If the action is terminated, out and err will have not
null values and the process exit code will be available at 'exitcode'.
Additionally, 'time' will be appended by "completed", "failed" or "terminated".

.. _result:

result - get action status
--------------------------

Checks the result of the action by it's UUID or returns the actions for the
specified unit.

Parameters:

* k - valid API key
* u - action UUID or
* i - unit ID

Additionally results may be filtered by:

* g=GROUP - unit group
* s=STATE - action status (Q - queued, R - running, F - finished)

Returns:

Same JSON dict as :ref:`action<action>`

Errors:

* 403 Forbidden - invalid API KEY
* 404 Not Found - unit doesn't exist, action with the specified UUID doesn't
  exist, or the key has no access to them

.. _terminate:

terminate - terminate action
----------------------------

Terminate action execution or cancel the action if it's still queued

Parameters:

* k - valid API key
* u - action UUID

Returns:

Returns JSON dict result="OK", if the action is terminated. If the action is
still queued, it will be canceled. result="ERROR" may occur if the action
termination is disabled in unit configuration.

Errors:

* 403 Forbidden - invalid API KEY
* 404 Not Found - action with the specified UUID doesn't exist (or already
  compelted), or the key has no access to it

.. _q_clean:

q_clean - clean up the action queue
-----------------------------------

Cancel all queued actions, keep the current action running

Parameters:

* k - valid API key
* i - unit ID

Returns JSON dict result="OK", if queue is cleaned.

Errors:

* 403 Forbidden - invalid API KEY
* 404 Not Found - unit doesn't exist, or the key has no access to it

.. _kill:

kill - clean up the queue and terminate the actions
--------------------------------------------------

Apart from canceling all queued commands, this function also terminates the
current running action.

Parameters:

* k - valid API key
* i - unit ID

Returns JSON dict result="OK", if the command completed successfully. If the
current action of the unit cannot be terminated by configuration, the notice
"pt" = "denied" will be returned additionally (even if there's no action
running)

Errors:

* 403 Forbidden - invalid API KEY
* 404 Not Found - unit doesn't exist, or the key has no access to it
