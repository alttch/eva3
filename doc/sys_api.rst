SYS API
*******

SYS API is a common API present in all EVA controllers. SYS API functions are
used to manage controller itself.

SYS API is called through URL request

**\http://<IP_address:Port>/sys-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

All functions can be called using GET and POST methods. When POST method is
used, the parameters can be passed to functions either as www-form or as JSON.

.. contents::

.. _s_test:

test - test API/key and get system info
=======================================

Test can be executed with any valid API key of the controller the function is
called to.

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

* **403 Forbidden** the key has no access to the API.

.. _s_cmd:

cmd - execute a remote command
==============================

Executes a :ref:`command script<cmd>` on the server where the controller is
installed.

Parameters:

* **k** API key with "allow=cmd" permission
* **c** name of the command script
* **a** command arguments (passed to the script)
* **w** wait (in seconds) before API call sends a response. This allows to try
        waiting until command finish
* **t** maximum time of command execution. If the command fails to finish
        within the specified time (in sec), it will be terminated

Returns JSON dict

.. code-block:: text

    {
       "args": [ "<specified>", "<command>", "<parameters>" ],
       "cmd": "<command>",
       "err": "<stderr output>",
       "exitcode": <script exit code>,
       "out": "<stdout output>",
       "status": "<current_status>",
       "time": {
           "<status1>": <UNIX_TIMESTAMP>,
           "<status2>": <UNIX_TIMESTAMP>
       },
       "timeout": "<specified_max_execution_time>"
    }

If API failed to wait for the command execution results (t < w), the status
will be returned as **"running"**. In case the command is complete, the status
will be one of the following:

* **completed** command succeeded
* **failed** command failed (exitcode > 0)
* **terminated** command is terminated by timeout/by system or the requested
                 script was not found

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_lock:

lock - lock token request
=========================

Lock tokens can be used similarly to file locking by the specific process. The
difference is that SYS API tokens can be:

* centralized for several systems (any EVA server can act as lock server)
* removed from outside
* automatically unlocked after the expiration time, if the initiator failed or
  forgot to release the lock

used to restrict parallel process starting or access to system files/resources.

Important: even if different EVA controllers are working on the same server,
their lock tokens are stored in different bases. To work with the token of each
subsystem, use SYS API on the respective address/port.

Parameters:

* **k** API key with "allow=lock" permissions
* **l** lock ID (arbitrary)
* **t** maximum timeout (seconds) to get token (optionally)
* **e** time after which token is automatically unlocked (if absent, token may
        be unlocked only via unlock function)

returns JSON dict { "result": "OK" }, if lock has been received or {
"result": "ERROR" }, if lock failed to be obtained

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_unlock:

unlock - release lock token
===========================

Releases the previously requested lock token.

Parameters:

* **k** API key with "allow=lock" permissions
* **l** lock token ID

returns JSON dict { "result" : "OK" }. In case token is already
unlocked, *remark = "notlocked"* note will be present in the result.

Errors:

* **403 Forbidden** the API key has no access to this function
* **404 Not Found** token not found

.. _s_log_rotate:

log_rotate - rotate controller's log file
=========================================

Rotates log file similarly to kill -HUP <controller_id>


Parameters:

* **k** API key with "sysfunc=yes" permissions

returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_log:

log_debug, log_info, log_warning, log_error, log_critical - write to the log
============================================================================

An external application can put a message in the logs on behalf of the
controller.

Parameters:

* **k** API key with "sysfunc=yes" permissions
* **m** message to log

returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_log_get:

log_get - get log records
=========================

This command allows to read log records from the controller. Log records are
stored in the controllers' memory until restart or the time (*keep_logmem*)
specified in controller configuration passes.

.. note::

    this doesn't allow you to obtain records stored in log files, only the
    records currently kept in memory

Parameters:

* **k** API key with "sysfunc=yes" permissions

Optionally:

* **l** log level (10 - debug, 20 - info, 30 - warning, 40 - error, 50 -
        critical)
* **t** get log records not older than *t* seconds
* **n** the maximum number of log records you want to obtain

returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_set_debug:

set_debug - switch debugging mode
=================================

Enables and disables debugging mode while the controller is running. After the
controller is restarted, this parameter is lost and controller switches back to
the mode specified in the configuration file.

Parameters:

* **k** API key with "sysfunc=yes" permissions
* **debug** 1 for enabling debug mode, 0 for disabling

returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_get_cvar:

get_cvar - get variable
=======================

Returns one or all user-defined variables.

Important: even if different EVA controllers are working on the same server,
they have different sets of variables To set the variables for each subsystem,
use SYS API on the respective address/port.

Parameters:

* **k** API key with masterkey permissions
* **i** variable name (if not specified, all variables will be returned)

Returns JSON dict

.. code-block:: json

    {
        "VARIABLE" : "VALUE"
    }

Errors:

* **403 Forbidden** the API key has no access to this function
* **404 Not Found** the specified variable is not defined

.. _s_set_cvar:

set_cvar - set variable value
=============================

Sets the value of user-defined variable.

Parameters:

* **k** API key with masterkey permissions
* **i** variable name
* **v** variable value (if omitted, variable is deleted)

returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_save:

save - save database and runtime configuration
==============================================

All modified items, their status, and configuration will be written to the
disk. If **exec_before_save** command is defined in the controller's
configuration file, it's called before saving and **exec_after_save** after
(e.g. to switch the partition to write mode and back to read-only).

Parameters:

* **k** API key with "sysfunc=yes" permissions

returns JSON dict { "result": "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

Notifier management
===================

These functions allow you to manage :doc:`notifiers<notifiers>` while EVA
component is running. All changes are applied temporarily and are discarded
after controller restart.

.. _s_notifiers:

notifiers - get list of notifiers
---------------------------------

Get the list of configured notifiers as well as their configuration.

Parameters:

* **k** API key with masterkey permissions

returns JSON array of the notifiers available on the controller.

Errors:

* **403 Forbidden** the API key has no access to this function

enable_notifier
---------------

Enables selected notifier

Parameters:

* **k** API key with masterkey permissions
* **i** notifier ID

returns JSON dict { "result": "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

disable_notifier
----------------

Disables selected notifier

Parameters:

* **k** API key with masterkey permissions
* **i** notifier ID

returns JSON dict { "result": "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

API key management
==================

Each EVA component allows you to manage its API keys. Keys, stored in
configuration files are called static and can not be managed. Also you can not
dynamically create keys with *masterkey* permissions.

Each EVA controller has its own API key list written in the local database of
the certain server by default. If you set same *userdb_file* value in the
controllers' configurations, they will use a common key list.

.. _s_list_keys:

list_keys - get API keys list
-----------------------------

Get the list of available API keys

Parameters:

* **k** API key with masterkey permissions

returns JSON array of the API keys available on the controller.

Errors:

* **403 Forbidden** the API key has no access to this function

create_key - create new API key
-------------------------------

Creates new dynamic API key.

Parameters:

* **k** API key with masterkey permissions
* **n** new API key ID, required

Optionally:

* **s** Allow system functions (*sysfunc*)
* **i** Item IDs, list or comma separated (*items*)
* **g** Item groups (*groups*)
* **a** Allow permissions (*cmd*, *device*, *lock* etc., *allow*)
* **hal** Hosts and networks allowed to use this key (*hosts_allow*), default:
  *0.0.0.0/0* (allow for all hosts)
* **has** Hosts and networks for which the key is automatically assigned if no
  key provided (*hosts_assign*)
* **pvt** :doc:`/sfa/sfa_pvt` files access list (*pvt*)
* **rpvt** :ref:`SFA remote files<sfa_rpvt>` access list (*rpvt*)

Returns serialized key dict in case of succcess or JSON dict { "result":
"ERROR" } in case of error.

Errors:

* **403 Forbidden** the API key has no access to this function

modify_key - modify existing API key
------------------------------------

Allows to modify existing dynamic API key.

Parameters:

* **k** API key with masterkey permissions
* **n** API key ID, required

Optionally:

* **s** Allow system functions (*sysfunc*)
* **i** Item IDs, list or comma separated (*items*)
* **g** Item groups (*groups*)
* **a** Allow permissions (*cmd*, *device*, *lock* etc., *allow*)
* **hal** Hosts and networks allowed to use this key (*hosts_allow*)
* **has** Hosts and networks for which the key is automatically assigned if
  no key provided (*hosts_assign*)
* **pvt** :doc:`/sfa/sfa_pvt` files access list (*pvt*)
* **rpvt** :ref:`SFA remote files<sfa_rpvt>` access list (*rpvt*)

Returns serialized key dict in case of succcess or JSON dict { "result":
"ERROR" } in case of error.

Errors:

* **403 Forbidden** the API key has no access to this function

regenerate_key - regenerate existing API key
--------------------------------------------

Allows to regenerate existing dynamic API key leaving its permissions
unchanged.

Parameters:

* **k** API key with masterkey permissions
* **n** API key ID, required

Returns serialized key dict in case of succcess or JSON dict { "result":
"ERROR" } in case of error.

Errors:

* **403 Forbidden** the API key has no access to this function

destroy_key - delete API key
----------------------------

Deletes dynamic API key from the database.

Parameters:

* **k** API key with masterkey permissions
* **n** API key ID, required

returns JSON dict { "result": "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

User management
===============

Apart from authorization via API keys, requests to API can be authorized using
login/password. A specific API key is assigned to each user (thhe same key can
be assigned to multiple users) and its permissions are stored during login
session.

The key assigned to user is used to authorize all the operations unless the
other key is specified in the request.

Each EVA controller has its own user list written in the local database of the
certain server by default. If you set same *userdb_file* value in the
controllers' configurations, they will use a common user list.

As far as controllers don't write anything to the database during user
authorization tasks, it can easily be stored on the network drive and used by
EVA controllers running on different hosts.

.. _s_list_users:

list_users - get users list
---------------------------

Get the list of the defined users and API keys assigned to them

Parameters:

* **k** API key with masterkey permissions

returns JSON array:

.. code-block:: json

    [
        {
            "key": "masterkey",
            "user": "admin"
        },
        {
            "key": "key1",
            "user": "eva"
        },
        {
           "key": "key1",
            "user": "john"
        },
        {
            "key": "op",
            "user": "operator"
        }
    ]

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_create_user:

create_user - create new user
-----------------------------

Creates a new user in the database

Parameters:

* **k** API key with masterkey permissions
* **u** user login
* **p** user password
* **a** API key to assign

returns JSON dict { "result" : "OK"}

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_set_user_password:

set_user_password - change user password
----------------------------------------

Changes user password

Parameters:

* **k** API key with masterkey permissions
* **u** user login
* **p** new password

returns JSON dict { "result" : "OK"}

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_set_user_key:

set_user_key - change assigned API key
--------------------------------------

Assigns another API key to user

Parameters:

* **k** API key with masterkey permissions
* **u** user login
* **a** API key to assign

returns JSON dict { "result" : "OK"}

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_destroy_user:

destroy_user - delete user
--------------------------

Deletes user from the database

Parameters:

* **k** API key with masterkey permissions
* **u** user login

returns JSON dict { "result" : "OK"}

Errors:

* **403 Forbidden** the API key has no access to this function

File operations in runtime
==========================

SYS API allows operations with any text files in "runtime" folder. According to
the program architecture, all files in this folder (except for databases) are
text(JSON). To simplify working with files via API calls all requests and
replies are made in text(JSON) format and no binary data is transferred.

For safety reasons these API functions must be enabled in advance with
*file_management=yes* param in "sysapi" section of the controller's
configuration file.

.. _s_file_get:

file_get - get file from runtime
--------------------------------

Gets a content of the file from runtime folder.

Parameters:

* **k** API key with masterkey permissions
* **i** path to file, relatively to runtime root, without / at the beginning

returns JSON dict:

.. code-block:: json

    {
        "data": "<FILE_CONTENT>",
        "file": "<FILE_NAME>",
        "result": "OK"
    }


Errors:

* **403 Forbidden** the API key has no access to this function
* **404 Not Found** the file doesn't exist

.. _s_file_put:

file_put - upload file into runtime
-----------------------------------

Puts a new file into runtime folder. If the file with such name exists, it will
be overwritten.

Parameters:

* **k** API key with masterkey permissions
* **i** path to file, relatively to runtime root, without / at the beginning
* **m** file content

returns JSON dict { "result" : "OK"}

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_file_set_exec:

file_set_exec - file exec permission management
-----------------------------------------------

Sets file permissions to allow its execution.

Parameters:

* **k** API key with masterkey permissions
* **i** path to file, relatively to runtime root, without / at the beginning
* **e** 0 to prohibit the file execution (permissions 0644), 1 - to allow
        (permissions 0755)

returns JSON dict { "result" : "OK"}

Errors:

* **403 Forbidden** the API key has no access to this function
* **404 Not Found** the file doesn't exist

.. _s_file_unlink:

file_unlink - file exec permission management
-----------------------------------------------

Deletes the file from the runtime folder.

Parameters:

* **k** API key with masterkey permissions
* **i** path to file, relatively to runtime root, without / at the beginning

returns JSON dict { "result" : "OK"}

Errors:

* **403 Forbidden** the API key has no access to this function
* **404 Not Found** the file doesn't exist
