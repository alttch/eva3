SFA API
=======

:doc:`SCADA Final Aggregator<sfa>` SFA API is called through URL request

**\http://<IP_address_SFA:Port>/sfa-api/function**

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

Functions passed to the remote controllers
------------------------------------------

The following functions are passed to the :ref:`connected remote
controllers<sfa_remote_c>` and return the result as-is.

Units control
~~~~~~~~~~~~~

* :ref:`action<uc_action>` - UC API call for :ref:`unit<unit>` control actions
* :ref:`action_toggle<uc_action_toggle>` - UC API call for :ref:`unit<unit>`
  control actions to toggle status
* :ref:`result<uc_result>` - UC API call to get action result by unit id or
  uuid
* :ref:`terminate<uc_terminate>` - UC API call to terminate current
  :ref:`unit<unit>` action
* :ref:`q_clean<uc_q_clean>` - UC API call to clean :ref:`unit<unit>` action
  queue
* :ref:`kill<uc_kill>` - UC API call to :ref:`unit<unit>` action queue and
  terminate the current action
* :ref:`disable_actions<uc_disable_actions>` - UC API call to disable
  :ref:`unit<unit>` actions
* :ref:`enable_actions<uc_enable_actions>` - UC API call to enable
  :ref:`unit<unit>` actions

Logic variables control
~~~~~~~~~~~~~~~~~~~~~~~

* :ref:`set<lm_set>` - LM API call to set :ref:`logic variable<lvar>` state
* :ref:`reset<lm_reset>` - LM API call to reset :ref:`logic variable<lvar>`
  state
* :ref:`clear<lm_clear>` - LM API call to clear :ref:`logic variable<lvar>`
  state
* :ref:`toggle<lm_toggle>` - LM API call to toggle :ref:`logic variable<lvar>`
  state

Macros control
~~~~~~~~~~~~~~

* :ref:`run<lm_run>` - LM API call to execute :doc:`logic control
  macro</lm/macros>`

Decision rules control
~~~~~~~~~~~~~~~~~~~~~~

* :ref:`list_rule_props<lm_list_rule_props>` - LM API call to list
  :doc:`decision rule</lm/decision_matrix>` props
* :ref:`set_rule_prop<lm_set_rule_prop>` - LM API call to set :doc:`decision
  rule</lm/decision_matrix>` prop

.. _sfa_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid :ref:`API KEY<sfa_apikey>`

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
        "product_code": "sfa",
        "product_name": "EVA SCADA Final Aggregator"
        "result": "OK",
        "system": "eva3-test1",
        "time": 1504489043.4566338,
        "version": "3.0.0"
    }

Errors:

* **403 Forbidden** the key has no access to the API

.. _sfa_reload_clients:

reload_clients - ask connected clients to reload
------------------------------------------------

This function sends to all connected clients a **reload** event asking them to
reload the interface.

All the connected clients receive the event with *subject="reload"* and
*data="asap"*. If the clients use :doc:`sfa_framework`, they must define
:ref:`eva_sfa_reload_handler<sfw_reload>` function.

Parameters:

* **k** masterkey

Returns result="OK" if the reload event is sent, or result="ERROR", if an error
occurs.

Errors:

* **403 Forbidden** invalid API KEY

.. _sfa_state:

state - get item state
----------------------

State of the known :doc:`item</items>` or all the items of the specified type
can be obtained using **state** command.

Parameters:

* **k** valid API key
* **p** item type (*U* for :ref:`unit<unit>`, *S* for :ref:`sensor<sensor>`,
  *LV* for :ref:`lvar<lvar>`, must always be specified
* **i** full item id (*group/id*), optional
* **g** group filter, optional :ref:`mqtt<mqtt_>` masks can be used, for
  example group1/#, group1/+/lamps)
  virtual, status_labels and action_enabled for unit)

Returns item status in JSON dict or array of dicts:

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
* **404 Not Found** item doesn't exist, or the key has no access to the item

.. _sfa_state_history:

state_history - get item state history
--------------------------------------

State history of the one :doc:`item</items>` or several items of the specified
type can be obtained using **state_history** command.

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

groups - get item group list
----------------------------

Get the list of the item groups. Useful e.g. for custom interfaces.

Parameters:

* **k** valid API key
* **p** item type (*U* for :ref:`unit<unit>`, *S* for :ref:`sensor<sensor>`,
  *LV* for :ref:`lvar<lvar>`), required

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

Get the list of all available :doc:`macros</lm/macros>`.

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

.. _sfa_list_remote:

list_remote - get a list of items from connected controllers
------------------------------------------------------------

Get a list of the items loaded from the connected
:ref:`controllers<sfa_remote_c>`.  Useful to debug the controller connections.

Parameters:

* **k** masterkey

optionally:

* **g** item group
* **p** item type (*U* for :ref:`unit<unit>`, *S* for :ref:`sensor<sensor>`,
  *LV* for :ref:`lvar<lvar>`)

Returns the JSON array of :ref:`units<unit>`, :ref:`sensors<sensor>` loaded
from the remote controllers. Additional field **controller_id** is present in
any item indicating the controller it's loaded from.

Errors:

* **403 Forbidden** invalid API KEY

.. _sfa_list_controllers:

list_controllers - get controllers list
---------------------------------------

Get the list of all connected :ref:`controllers<sfa_remote_c>`.

Parameters:

* **k** valid API key
* **g** controller type (*uc* or *lm*, optional)

Returns JSON array:

.. code-block:: json

    [
        {
        "description": "<controller_description>",
        "full_id": "<type/controller_id>",
        "group": "<type>",
        "id": "<controller_id>",
        "oid": "remote_<type>:<type>/<controller_id>",
        "type": "remote_<type>"
        }
    ]

Errors:

* **403 Forbidden** invalid API KEY

.. _sfa_list_controller_props:

list_controller_props - get editable controller parameters
----------------------------------------------------------

Allows to get all editable parameters of the connected
:ref:`controller<sfa_remote_c>`.

* **k** masterkey
* **i** controller id

Errors:

* **403 Forbidden** invalid API KEY
* **404 Not Found** controller doesn't exist

.. _sfa_set_controller_prop:

set_controller_prop - set controller parameters
-----------------------------------------------

Allows to set configuration parameters of the connected controller.

Parameters:

* **k** masterkey
* **i** controller id
* **p** controller configuration param
* **v** param value

Returns result="OK" if the parameter is set, or result="ERROR", if an error
occurs.

Errors:

* **403 Forbidden** invalid API KEY

.. _sfa_append_controller:

append_controller - connect remote controller
---------------------------------------------

Connects remote :ref:`controller<sfa_remote_c>` to the local.

Parameters:

* **k** masterkey
* **uri** API uri (*proto://host:port*)
* **a** remote controller API key (\$key to use local key)

optionally:

* **m** :ref:`MQTT notifier<mqtt_>` to exchange item states in real time
* **s** *True*/*False* (*1*/*0*) verify remote SSL certificate or pass invalid
* **t** timeout (seconds) for the remote controller API calls
* **save=1** save connected controller configuration on the disk immediately
  after creation

Returns result="OK" if the controller is connected, or result="ERROR", if an
error occurred.

The remote controller id is obtained and set automatically according to its
hostname or **name** field in the controller configuration. The remote
controller id can't be changed.

Errors:

* **403 Forbidden** invalid API KEY

.. _sfa_remove_controller:

remove_controller - disconnect remote controller
------------------------------------------------

Disconnects the remote :ref:`controller<sfa_remote_c>`.

Parameters:

* **k** masterkey
* **i** controller id

Returns result="OK" if the controller is disconnected, or result="ERROR", if an
error occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. _sfa_reload_controller:

reload_controller - reload items from UC
----------------------------------------

Allows to immediately reload all the :doc:`items</items>`,
:doc:`macros</lm/macros>` and their status from the remote
:ref:`controller<sfa_remote_c>`.

Parameters:

* **k** masterkey
* **i** controller id

Returns result="OK" if the controller is deleted, or result="ERROR", if an
error occurred.

Errors:

* **403 Forbidden** invalid API KEY

.. include:: ../userauth.rst

