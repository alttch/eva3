Common methods
**************

Common methods are present in all EVA controllers. They are used to manage controller itself. 

RESTful API equivalent calls can be found in corresponding component RESTful API docs.


API basics
==========

JSON RPC
--------

`JSON RPC 2.0 <https://www.jsonrpc.org/specification>`_ protocol is the primary
EVA ICS API protocol. Note that default JSON RPC result is *{ "ok": true }*
(instead of *{ "result": "OK" }* in the direct API).  There's no *{ result:
"ERROR" }* responses, as JSON RPC sends errors in "error" field.

If JSON RPC request is called without ID and server should not return a result,
it will return http response with a code *202 Accepted*.

.. note::

    JSON RPC is recommended way to use EVA ICS API, unless direct method
    calling or RESTful is really required.

JSON RPC API URL:

    **\http://<ip_address:port>/jrpc**

    or

    **\http://<ip_address:port>**

    (all POST requests to the root URI are processed as JSON RPC)

JSON RPC payload encoding
~~~~~~~~~~~~~~~~~~~~~~~~~

EVA ICS supports JSON RPC payloads, encoded as generic JSON and as `MessagePack
<https://msgpack.org/>`_. MessagePack encoding works faster, requires less
bandwidth and is highly recommended to use.

To call API methods with MessagePack-encoded payloads, use *Content-Type:
application/msgpack* HTTP request header.

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

.. warning::

    It's highly not recommended to perform long API calls, calling API
    functions from JavaScript in a web browser (e.g. giving "w" param to action
    methods to wait until action finish). Web browser may repeat API call
    continuously, which may lead to absolutely unexpected behavior.

JSON RPC via HTTP GET
~~~~~~~~~~~~~~~~~~~~~

Embedded equipment sometimes can send HTTP GET requests only. JSON RPC API
supports such calls as well.

To make JSON RPC API request with HTTP get, send it to:

    **\http://<ip_address:port>/jrpc?i=ID&m=METHOD&p=PARAMS**

where:

* **ID** request ID (any custom value). If not specified, API response isn't
  sent back
* **METHOD** JSON RPC method to call
* **PARAMS** method params, as url-encoded JSON

E.g. the following HTTP GET request will invoke method "test" with request id=1
and params *{ "k": "mykey" }*:

    *\http://<ip_address:port>/jrpc?i=1&m=test&p=%7B%22k%22%3A%22mykey%22%7D*

.. note::

    JSON RPC API calls via HTTP GET are insecure, limited to 2048 bytes and can
    not be batch. Use JSON RPC via HTTP POST with JSON or MessagePack payload
    always when possible.

Direct API
----------

.. warning::

    Direct method calling is deprecated and scheduled to be removed (not
    implemented) in EVA ICS v4. Use JSON RPC API, whenever it is possible.

Common methods functions are called through URL request

    **\http://<ip_address:port>/sys-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

Direct API responses
~~~~~~~~~~~~~~~~~~~~

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

.. contents::

.. _sysapi_cat_general:

General functions
=================



.. _sysapi_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid API key of the controller the function is called to.

For SFA, the result section "connected" contains connection status of remote controllers. The API key must have an access either to "uc" and "lm" groups ("remote_uc:uc" and "remote_lm:lm") or to particular controller oids.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/test.req-jrpc
    :response: http-examples/jrpc/sysapi/test.resp-jrpc

Parameters:

* **k** any valid API key

Returns:

JSON dict with system info and current API key permissions (for masterkey only { "master": true } is returned)

.. _sysapi_save:

save - save database and runtime configuration
----------------------------------------------

All modified items, their status, and configuration will be written to the disk. If **exec_before_save** command is defined in the controller's configuration file, it's called before saving and **exec_after_save** after (e.g. to switch the partition to write mode and back to read-only).

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/save.req-jrpc
    :response: http-examples/jrpc/sysapi/save.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions

.. _sysapi_clear_lang_cache:

clear_lang_cache - Clear language cache
---------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/clear_lang_cache.req-jrpc
    :response: http-examples/jrpc/sysapi/clear_lang_cache.resp-jrpc

.. _sysapi_cmd:

cmd - execute a remote system command
-------------------------------------

Executes a :ref:`command script<cmd>` on the server where the controller is installed.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/cmd.req-jrpc
    :response: http-examples/jrpc/sysapi/cmd.resp-jrpc

Parameters:

* **k** API key with *allow=cmd* permissions
* **c** name of the command script

Optionally:

* **a** string of command arguments, separated by spaces (passed to the script) or array (list)
* **w** wait (in seconds) before API call sends a response. This allows to try waiting until command finish
* **t** maximum time of command execution. If the command fails to finish within the specified time (in sec), it will be terminated
* **s** STDIN data

.. _sysapi_install_pkg:

install_pkg - install a package
-------------------------------

Installs the :doc:`package </packages>`

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/install_pkg.req-jrpc
    :response: http-examples/jrpc/sysapi/install_pkg.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** package name
* **m** package content (base64-encoded tar/tgz)
* **o** package setup options
* **w** wait (in seconds) before API call sends a response. This allows to try waiting until the package is installed

.. _sysapi_list_plugins:

list_plugins - get list of loaded core plugins
----------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/list_plugins.req-jrpc
    :response: http-examples/jrpc/sysapi/list_plugins.resp-jrpc

Parameters:

* **k** API key with *master* permissions

Returns:

list with plugin module information

.. _sysapi_set_debug:

set_debug - switch debugging mode
---------------------------------

Enables and disables debugging mode while the controller is running. After the controller is restarted, this parameter is lost and controller switches back to the mode specified in the configuration file.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/set_debug.req-jrpc
    :response: http-examples/jrpc/sysapi/set_debug.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **debug** true for enabling debug mode, false for disabling

.. _sysapi_shutdown_core:

shutdown_core - shutdown the controller
---------------------------------------

Controller process will be exited and then (should be) restarted by watchdog. This allows to restart controller remotely.

For MQTT API calls a small shutdown delay usually should be specified to let the core send the correct API response.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/shutdown_core.req-jrpc
    :response: http-examples/jrpc/sysapi/shutdown_core.resp-jrpc

Returns:

current boot id. This allows client to check is the controller restarted later, by comparing returned boot id and new boot id (obtained with "test" command)

.. _sysapi_login:

login - log in and get authentication token
-------------------------------------------

Obtains authentication :doc:`token</api_tokens>` which can be used in API calls instead of API key.

If both **k** and **u** args are absent, but API method is called with HTTP request, which contain HTTP header for basic authorization, the function will try to parse it and log in user with credentials provided.

If authentication token is specified, the function will check it and return token information if it is valid.

If both token and credentials (user or API key) are specified, the function will return the token to normal mode.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/login.req-jrpc
    :response: http-examples/jrpc/sysapi/login.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/logout.req-jrpc
    :response: http-examples/jrpc/sysapi/logout.resp-jrpc

Parameters:

* **k** valid token

.. _sysapi_set_token_readonly:

set_token_readonly - Set token read-only
----------------------------------------

Applies read-only mode for token. In read-only mode, only read-only functions work, others return result_token_restricted(15).

The method works for token-authenticated API calls only.

To exit read-only mode, user must either re-login or, to keep the current token, call "login" API method with both token and user credentials.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/set_token_readonly.req-jrpc
    :response: http-examples/jrpc/sysapi/set_token_readonly.resp-jrpc

.. _sysapi_get_neighbor_clients:

get_neighbor_clients - Get neighbor clients
-------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/get_neighbor_clients.req-jrpc
    :response: http-examples/jrpc/sysapi/get_neighbor_clients.resp-jrpc

Parameters:

* **k** valid API key
* **i** neightbor client id


.. _sysapi_cat_cvar:

CVARs
=====



.. _sysapi_get_cvar:

get_cvar - get the value of user-defined variable
-------------------------------------------------

.. note::

    Even if different EVA controllers are working on the same     server, they have different sets of variables To set the variables     for each subsystem, use SYS API on the respective address/port.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/get_cvar.req-jrpc
    :response: http-examples/jrpc/sysapi/get_cvar.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/set_cvar.req-jrpc
    :response: http-examples/jrpc/sysapi/set_cvar.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/get_lock.req-jrpc
    :response: http-examples/jrpc/sysapi/get_lock.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/lock.req-jrpc
    :response: http-examples/jrpc/sysapi/lock.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/unlock.req-jrpc
    :response: http-examples/jrpc/sysapi/unlock.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/log.req-jrpc
    :response: http-examples/jrpc/sysapi/log.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **l** log level
* **m** message text

.. _sysapi_log_debug:

log_debug - put debug message to log file
-----------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/log_debug.req-jrpc
    :response: http-examples/jrpc/sysapi/log_debug.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_info:

log_info - put info message to log file
---------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/log_info.req-jrpc
    :response: http-examples/jrpc/sysapi/log_info.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_warning:

log_warning - put warning message to log file
---------------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/log_warning.req-jrpc
    :response: http-examples/jrpc/sysapi/log_warning.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_error:

log_error - put error message to log file
-----------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/log_error.req-jrpc
    :response: http-examples/jrpc/sysapi/log_error.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_critical:

log_critical - put critical message to log file
-----------------------------------------------

An external application can put a message in the logs on behalf of the controller.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/log_critical.req-jrpc
    :response: http-examples/jrpc/sysapi/log_critical.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions
* **m** message text

.. _sysapi_log_get:

log_get - get records from the controller log
---------------------------------------------

Log records are stored in the controllers’ memory until restart or the time (keep_logmem) specified in controller configuration passes.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/log_get.req-jrpc
    :response: http-examples/jrpc/sysapi/log_get.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions

Optionally:

* **l** log level (10 - debug, 20 - info, 30 - warning, 40 - error, 50 - critical)
* **t** get log records not older than t seconds
* **n** the maximum number of log records you want to obtain
* **x** regex pattern filter

.. _sysapi_log_rotate:

log_rotate - rotate log file
----------------------------

Deprecated, not required since 3.3.0

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/log_rotate.req-jrpc
    :response: http-examples/jrpc/sysapi/log_rotate.resp-jrpc

Parameters:

* **k** API key with *sysfunc=yes* permissions

.. _sysapi_api_log_get:

api_log_get - get API call log
------------------------------

* API call with master permission returns all records requested

* API call with other API key returns records for the specified key   only

* API call with an authentication token returns records for the   current authorized user

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/api_log_get.req-jrpc
    :response: http-examples/jrpc/sysapi/api_log_get.resp-jrpc

Parameters:

* **k** any valid API key

Optionally:

* **s** start time (timestamp or ISO or e.g. 1D for -1 day)
* **e** end time (timestamp or ISO or e.g. 1D for -1 day)
* **n** records limit
* **t** time format ("iso" or "raw" for unix timestamp, default is "raw")
* **f** record filter (requires API key with master permission)

Returns:

List of API calls

Note: API call params are returned as string and can be invalid JSON data as they're always truncated to 512 symbols in log database

Record filter should be specified either as string (k1=val1,k2=val2) or as a dict. Valid fields are:

* gw: filter by API gateway

* ip: filter by caller IP

* auth: filter by authentication type

* u: filter by user

* utp: filter by user type

* ki: filter by API key ID

* func: filter by API function

* params: filter by API call params (matches if field contains value)

* status: filter by API call status


.. _sysapi_cat_keys:

API keys
========



.. _sysapi_create_key:

create_key - create API key
---------------------------

API keys are defined statically in EVA registry config/<controller>/apikeys tree or can be created with API and stored in the user database.

Keys with the master permission can not be created.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/create_key.req-jrpc
    :response: http-examples/jrpc/sysapi/create_key.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/destroy_key.req-jrpc
    :response: http-examples/jrpc/sysapi/destroy_key.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** API key ID

.. _sysapi_list_key_props:

list_key_props - list API key permissions
-----------------------------------------

Lists API key permissons (including a key itself)

.. note::

    API keys defined in EVA registry can not be managed with API.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/list_key_props.req-jrpc
    :response: http-examples/jrpc/sysapi/list_key_props.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** API key ID
* **save** save configuration immediately

.. _sysapi_list_keys:

list_keys - list API keys
-------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/list_keys.req-jrpc
    :response: http-examples/jrpc/sysapi/list_keys.resp-jrpc

Parameters:

* **k** API key with *master* permissions

.. _sysapi_regenerate_key:

regenerate_key - regenerate API key
-----------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/regenerate_key.req-jrpc
    :response: http-examples/jrpc/sysapi/regenerate_key.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** API key ID

Returns:

JSON dict with new key value in "key" field

.. _sysapi_set_key_prop:

set_key_prop - set API key permissions
--------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/set_key_prop.req-jrpc
    :response: http-examples/jrpc/sysapi/set_key_prop.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/create_user.req-jrpc
    :response: http-examples/jrpc/sysapi/create_user.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **u** user login
* **p** user password
* **a** API key to assign (key id, not a key itself)

.. _sysapi_destroy_user:

destroy_user - delete user account
----------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/destroy_user.req-jrpc
    :response: http-examples/jrpc/sysapi/destroy_user.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **u** user login

.. _sysapi_get_user:

get_user - get user account info
--------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/get_user.req-jrpc
    :response: http-examples/jrpc/sysapi/get_user.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **u** user login

.. _sysapi_list_users:

list_users - list user accounts
-------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/list_users.req-jrpc
    :response: http-examples/jrpc/sysapi/list_users.resp-jrpc

Parameters:

* **k** API key with *master* permissions

.. _sysapi_set_user_key:

set_user_key - assign API key to user
-------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/set_user_key.req-jrpc
    :response: http-examples/jrpc/sysapi/set_user_key.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **u** user login
* **a** API key to assign (key id, not a key itself) or multiple keys, comma separated

.. _sysapi_set_user_password:

set_user_password - set user password
-------------------------------------

Either master key and user login must be specified or a user must be logged in and a session token used

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/set_user_password.req-jrpc
    :response: http-examples/jrpc/sysapi/set_user_password.resp-jrpc

Parameters:

* **k** master key or token
* **u** user login
* **p** new password

.. _sysapi_list_tokens:

list_tokens - List active session tokens
----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/list_tokens.req-jrpc
    :response: http-examples/jrpc/sysapi/list_tokens.resp-jrpc

Parameters:

* **k** API key with *master* permissions

.. _sysapi_drop_tokens:

drop_tokens - Drop session token(s)
-----------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/drop_tokens.req-jrpc
    :response: http-examples/jrpc/sysapi/drop_tokens.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **a** session token or
* **u** user name or
* **i** API key id


.. _sysapi_cat_notifiers:

Notifier management
===================



.. _sysapi_disable_notifier:

disable_notifier - disable notifier
-----------------------------------

.. note::

    The notifier is disabled until controller restart. To disable     notifier permanently, use notifier management CLI.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/disable_notifier.req-jrpc
    :response: http-examples/jrpc/sysapi/disable_notifier.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** notifier ID

.. _sysapi_enable_notifier:

enable_notifier - enable notifier
---------------------------------

.. note::

    The notifier is enabled until controller restart. To enable     notifier permanently, use notifier management CLI.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/enable_notifier.req-jrpc
    :response: http-examples/jrpc/sysapi/enable_notifier.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** notifier ID

.. _sysapi_get_notifier:

get_notifier - get notifier configuration
-----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/get_notifier.req-jrpc
    :response: http-examples/jrpc/sysapi/get_notifier.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** notifier ID

.. _sysapi_list_notifiers:

list_notifiers - list notifiers
-------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/list_notifiers.req-jrpc
    :response: http-examples/jrpc/sysapi/list_notifiers.resp-jrpc

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
    :request: http-examples/jrpc/sysapi/file_put.req-jrpc
    :response: http-examples/jrpc/sysapi/file_put.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** relative path (without first slash)
* **m** file content (plain text or base64-encoded)
* **b** if True - put binary file (decode base64)

.. _sysapi_file_set_exec:

file_set_exec - set file exec permission
----------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/file_set_exec.req-jrpc
    :response: http-examples/jrpc/sysapi/file_set_exec.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** relative path (without first slash)
* **e** *false* for 0x644, *true* for 0x755 (executable)

.. _sysapi_file_get:

file_get - get file contents from runtime folder
------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/file_get.req-jrpc
    :response: http-examples/jrpc/sysapi/file_get.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** relative path (without first slash)
* **b** if True - force getting binary file (base64-encode content)

.. _sysapi_file_unlink:

file_unlink - delete file from runtime folder
---------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/file_unlink.req-jrpc
    :response: http-examples/jrpc/sysapi/file_unlink.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **i** relative path (without first slash)


.. _sysapi_cat_corescript:

Core scripts
============



.. _sysapi_list_corescript_mqtt_topics:

list_corescript_mqtt_topics - List MQTT topics core scripts react on
--------------------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/list_corescript_mqtt_topics.req-jrpc
    :response: http-examples/jrpc/sysapi/list_corescript_mqtt_topics.resp-jrpc

Parameters:

* **k** API key with *master* permissions

.. _sysapi_reload_corescripts:

reload_corescripts - Reload core scripts if some was added or deleted
---------------------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/reload_corescripts.req-jrpc
    :response: http-examples/jrpc/sysapi/reload_corescripts.resp-jrpc

Parameters:

* **k** API key with *master* permissions

.. _sysapi_subscribe_corescripts_mqtt:

subscribe_corescripts_mqtt - Subscribe core scripts to MQTT topic
-----------------------------------------------------------------

The method subscribes core scripts to topic of default MQTT notifier (eva_1). To specify another notifier, set topic as <notifer_id>:<topic>

..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/subscribe_corescripts_mqtt.req-jrpc
    :response: http-examples/jrpc/sysapi/subscribe_corescripts_mqtt.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **t** MQTT topic ("+" and "#" masks are supported)
* **q** MQTT topic QoS
* **save** save core script config after modification

.. _sysapi_unsubscribe_corescripts_mqtt:

unsubscribe_corescripts_mqtt - Unsubscribe core scripts from MQTT topic
-----------------------------------------------------------------------



..  http:example:: curl wget httpie python-requests
    :request: http-examples/jrpc/sysapi/unsubscribe_corescripts_mqtt.req-jrpc
    :response: http-examples/jrpc/sysapi/unsubscribe_corescripts_mqtt.resp-jrpc

Parameters:

* **k** API key with *master* permissions
* **t** MQTT topic ("+" and "#" masks are allowed)
* **save** save core script config after modification


.. _sysapi_cat_registry:

Registry management
===================



.. _sysapi_registry_safe_purge:

registry_safe_purge - Safely purge registry database
----------------------------------------------------

Clears registry trash and invalid files. Keeps broken keys

Parameters:

* **k** API key with *sysfunc=yes* permissions

