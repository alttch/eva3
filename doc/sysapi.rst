SYS API
**************

SYS API is a common API present in all EVA controllers. SYS API functions are used to manage controller itself. 

RESTful API equivalent calls can be found in corresponding component RESTful API docs.


API basics
==========

Standard API (direct method calling)
--------------------------------------

SYS API functions are called through URL request

    **\http://<ip_address:port>/sys-api/function**

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

    **\http://<ip_address:port>/jrpc**

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

.. _sysapi_cat_general:

General functions
=================



.. _sysapi_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid API key of the controller the function is called to.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/test.req
    :response: http-examples/sysapi/test.resp

Parameters:

* **k** any valid API key

Returns:

JSON dict with system info and current API key permissions (for masterkey only { "master": true } is returned)

.. _sysapi_save:

save - save database and runtime configuration
----------------------------------------------

All modified items, their status, and configuration will be written to the disk. If **exec_before_save** command is defined in the controller's configuration file, it's called before saving and **exec_after_save** after (e.g. to switch the partition to write mode and back to read-only).

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/save.req
    :response: http-examples/sysapi/save.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions

.. _sysapi_cmd:

cmd - execute a remote system command
-------------------------------------

Executes a :ref:`command script<cmd>` on the server where the controller is installed.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/cmd.req
    :response: http-examples/sysapi/cmd.resp

Parameters:

* **k** API key with *allow=cmd* permissions
* **c** name of the command script

Optionally:

* **a** string of command arguments, separated by spaces (passed to the script)
* **w** wait (in seconds) before API call sends a response. This allows to try waiting until command finish
* **t** maximum time of command execution. If the command fails to finish within the specified time (in sec), it will be terminated

.. _sysapi_set_debug:

set_debug - switch debugging mode
---------------------------------

Enables and disables debugging mode while the controller is running. After the controller is restarted, this parameter is lost and controller switches back to the mode specified in the configuration file.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/set_debug.req
    :response: http-examples/sysapi/set_debug.resp

Parameters:

* **k** API key with *master* permissions
* **debug** true for enabling debug mode, false for disabling

.. _sysapi_shutdown_core:

shutdown_core - shutdown the controller
---------------------------------------

Controller process will be exited and then (should be) restarted by watchdog. This allows to restart controller remotely.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/shutdown_core.req
    :response: http-examples/sysapi/shutdown_core.resp

Parameters:

* **k** API key with *master* permissions

.. _sysapi_login:

login - log in and get authentication token
-------------------------------------------

Obtains authentication :doc:`token</api_tokens>` which can be used in API calls instead of API key.

If both **k** and **u** args are absent, but API method is called with HTTP request, which contain HTTP header for basic authorization, the function will try to parse it and log in user with credentials provided.

If authentication token is specified, the function will check it and return token information if it is valid.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/login.req
    :response: http-examples/sysapi/login.resp

Parameters:

* **k** valid API key or
* **u** user login
* **p** user password
* **a** authentication token

Returns:

A dict, containing API key ID and authentication token

.. _sysapi_logout:

logout - log out and purge authentication token
-----------------------------------------------

Purges authentication :doc:`token</api_tokens>`

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/logout.req
    :response: http-examples/sysapi/logout.resp

Parameters:

* **k** valid token


.. _sysapi_cat_cvar:

CVARs
=====



.. _sysapi_get_cvar:

get_cvar - get the value of user-defined variable
-------------------------------------------------

.. note::

    Even if different EVA controllers are working on the same     server, they have different sets of variables To set the variables     for each subsystem, use SYS API on the respective address/port.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/get_cvar.req
    :response: http-examples/sysapi/get_cvar.resp

Parameters:

* **k** API key with *master* permissions

Optionally:

* **i** variable name

Returns:

Dict containing variable and its value. If no varible name was specified, all cvars are returned.

.. _sysapi_set_cvar:

set_cvar - set the value of user-defined variable
-------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/set_cvar.req
    :response: http-examples/sysapi/set_cvar.resp

Parameters:

* **k** API key with *master* permissions
* **i** variable name

Optionally:

* **v** variable value (if not specified, variable is deleted)


.. _sysapi_cat_lock:

Locking functions
=================



.. _sysapi_get_lock:

get_lock - get lock status
--------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/get_lock.req
    :response: http-examples/sysapi/get_lock.resp

Parameters:

* **k** API key with *allow=lock* permissions
* **l** lock id

.. _sysapi_lock:

lock - acquire lock
-------------------

Locks can be used similarly to file locking by the specific process. The difference is that SYS API tokens can be:

* centralized for several systems (any EVA server can act as lock     server)

* removed from outside

* automatically unlocked after the expiration time, if the initiator     failed or forgot to release the lock

used to restrict parallel process starting or access to system files/resources. LM PLC :doc:`macro</lm/macros>` share locks with extrnal scripts.

.. note::

    Even if different EVA controllers are working on the same server,     their lock tokens are stored in different bases. To work with the     token of each subsystem, use SYS API on the respective     address/port.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/lock.req
    :response: http-examples/sysapi/lock.resp

Parameters:

* **k** API key with *allow=lock* permissions
* **l** lock id

Optionally:

* **t** maximum time (seconds) to acquire lock
* **e** time after which lock is automatically released (if absent, lock may be released only via unlock function)

.. _sysapi_unlock:

unlock - release lock
---------------------

Releases the previously acquired lock.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/unlock.req
    :response: http-examples/sysapi/unlock.resp

Parameters:

* **k** API key with *allow=lock* permissions
* **l** lock id


.. _sysapi_cat_logs:

Logging
=======



.. _sysapi_log:

log - put message to log file
-----------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/log.req
    :response: http-examples/sysapi/log.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **l** log level
* **m** message text

.. _sysapi_log_debug:

log_debug - put debug message to log file
-----------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/log_debug.req
    :response: http-examples/sysapi/log_debug.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_info:

log_info - put info message to log file
---------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/log_info.req
    :response: http-examples/sysapi/log_info.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_warning:

log_warning - put warning message to log file
---------------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/log_warning.req
    :response: http-examples/sysapi/log_warning.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_error:

log_error - put error message to log file
-----------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/log_error.req
    :response: http-examples/sysapi/log_error.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_critical:

log_critical - put critical message to log file
-----------------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/log_critical.req
    :response: http-examples/sysapi/log_critical.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_get:

log_get - get records from the controller log
---------------------------------------------

Log records are stored in the controllers’ memory until restart or the time (keep_logmem) specified in controller configuration passes.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/log_get.req
    :response: http-examples/sysapi/log_get.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions

Optionally:

* **l** log level (10 - debug, 20 - info, 30 - warning, 40 - error, 50 - critical)
* **t** get log records not older than t seconds
* **n** the maximum number of log records you want to obtain

.. _sysapi_log_rotate:

log_rotate - rotate log file
----------------------------

Equal to kill -HUP <controller_process_pid>.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/log_rotate.req
    :response: http-examples/sysapi/log_rotate.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions


.. _sysapi_cat_keys:

API keys
========



.. _sysapi_create_key:

create_key - create API key
---------------------------

API keys are defined statically in etc/<controller>_apikeys.ini file as well as can be created with API and stored in user database.

Keys with master permission can not be created.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/create_key.req
    :response: http-examples/sysapi/create_key.resp

Parameters:

* **k** API key with *master* permissions
* **i** API key ID
* **save** save configuration immediately

Returns:

JSON with serialized key object

.. _sysapi_destroy_key:

destroy_key - delete API key
----------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/destroy_key.req
    :response: http-examples/sysapi/destroy_key.resp

Parameters:

* **k** API key with *master* permissions
* **i** API key ID

.. _sysapi_list_key_props:

list_key_props - list API key permissions
-----------------------------------------

Lists API key permissons (including a key itself)

.. note::

    API keys, defined in etc/<controller>_apikeys.ini file can not be     managed with API.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/list_key_props.req
    :response: http-examples/sysapi/list_key_props.resp

Parameters:

* **k** API key with *master* permissions
* **i** API key ID
* **save** save configuration immediately

.. _sysapi_list_keys:

list_keys - list API keys
-------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/list_keys.req
    :response: http-examples/sysapi/list_keys.resp

Parameters:

* **k** API key with *master* permissions

.. _sysapi_regenerate_key:

regenerate_key - regenerate API key
-----------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/regenerate_key.req
    :response: http-examples/sysapi/regenerate_key.resp

Parameters:

* **k** API key with *master* permissions
* **i** API key ID

Returns:

JSON dict with new key value in "key" field

.. _sysapi_set_key_prop:

set_key_prop - set API key permissions
--------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/set_key_prop.req
    :response: http-examples/sysapi/set_key_prop.resp

Parameters:

* **k** API key with *master* permissions
* **i** API key ID
* **p** property
* **v** value (if none, permission will be revoked)
* **save** save configuration immediately


.. _sysapi_cat_users:

User accounts
=============



.. _sysapi_create_user:

create_user - create user account
---------------------------------

.. note::

    All changes to user accounts are instant, if the system works in     read/only mode, set it to read/write before performing user     management.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/create_user.req
    :response: http-examples/sysapi/create_user.resp

Parameters:

* **k** API key with *master* permissions
* **u** user login
* **p** user password
* **a** API key to assign (key id, not a key itself)

.. _sysapi_destroy_user:

destroy_user - delete user account
----------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/destroy_user.req
    :response: http-examples/sysapi/destroy_user.resp

Parameters:

* **k** API key with *master* permissions
* **u** user login

.. _sysapi_get_user:

get_user - get user account info
--------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/get_user.req
    :response: http-examples/sysapi/get_user.resp

Parameters:

* **k** API key with *master* permissions
* **u** user login

.. _sysapi_list_users:

list_users - list user accounts
-------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/list_users.req
    :response: http-examples/sysapi/list_users.resp

Parameters:

* **k** API key with *master* permissions

.. _sysapi_set_user_key:

set_user_key - assign API key to user
-------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/set_user_key.req
    :response: http-examples/sysapi/set_user_key.resp

Parameters:

* **k** API key with *master* permissions
* **u** user login
* **a** API key to assign (key id, not a key itself)

.. _sysapi_set_user_password:

set_user_password - set user password
-------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/set_user_password.req
    :response: http-examples/sysapi/set_user_password.resp

Parameters:

* **k** API key with *master* permissions
* **u** user login
* **p** new password


.. _sysapi_cat_notifiers:

Notifier management
===================



.. _sysapi_disable_notifier:

disable_notifier - disable notifier
-----------------------------------

.. note::

    The notifier is disabled until controller restart. To disable     notifier permanently, use notifier management CLI.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/disable_notifier.req
    :response: http-examples/sysapi/disable_notifier.resp

Parameters:

* **k** API key with *master* permissions
* **i** notifier ID

.. _sysapi_enable_notifier:

enable_notifier - enable notifier
---------------------------------

.. note::

    The notifier is enabled until controller restart. To enable     notifier permanently, use notifier management CLI.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/enable_notifier.req
    :response: http-examples/sysapi/enable_notifier.resp

Parameters:

* **k** API key with *master* permissions
* **i** notifier ID

.. _sysapi_get_notifier:

get_notifier - get notifier configuration
-----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/get_notifier.req
    :response: http-examples/sysapi/get_notifier.resp

Parameters:

* **k** API key with *master* permissions
* **i** notifier ID

.. _sysapi_list_notifiers:

list_notifiers - list notifiers
-------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/list_notifiers.req
    :response: http-examples/sysapi/list_notifiers.resp

Parameters:

* **k** API key with *master* permissions


.. _sysapi_cat_files:

File management
===============



.. _sysapi_file_put:

file_put - put file to runtime folder
-------------------------------------

Puts a new file into runtime folder. If the file with such name exists, it will be overwritten. As all files in runtime are text, binary data can not be put.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/file_put.req
    :response: http-examples/sysapi/file_put.resp

Parameters:

* **k** API key with *master* permissions
* **i** relative path (without first slash)
* **m** file content

.. _sysapi_file_set_exec:

file_set_exec - set file exec permission
----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/file_set_exec.req
    :response: http-examples/sysapi/file_set_exec.resp

Parameters:

* **k** API key with *master* permissions
* **i** relative path (without first slash)
* **e** *false* for 0x644, *true* for 0x755 (executable)

.. _sysapi_file_get:

file_get - get file contents from runtime folder
------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/file_get.req
    :response: http-examples/sysapi/file_get.resp

Parameters:

* **k** API key with *master* permissions
* **i** relative path (without first slash)

.. _sysapi_file_unlink:

file_unlink - delete file from runtime folder
---------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/file_unlink.req
    :response: http-examples/sysapi/file_unlink.resp

Parameters:

* **k** API key with *master* permissions
* **i** relative path (without first slash)

