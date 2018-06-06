UC API
======

:doc:`Universal Controller<uc>` UC API is called through URL request

*\http://<IP_address_UC:Port>/uc-api/function?parameters*

If SSL is allowed in the controller configuration file, you can also use https
calls.

All functions can be called using GET and POST methods.

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid API KEY

Parameters:

* k - valid API key

Returns JSON-dict with system info and current API key permissions (for
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

Returns item status in JSON-dict or array of dicts:

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

