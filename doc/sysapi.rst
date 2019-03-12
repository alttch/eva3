SYS API
**************

SYS API is a common API present in all EVA controllers. SYS API functions are used to manage controller itself.

API basics
==========

Standard API (direct function calling)
--------------------------------------

SYS API functions are called through URL request

    **\http://<ip_address:port>/sys-api/function**

If SSL is allowed in the controller configuration file, you can also use https
calls.

All API functions can be called using GET and POST. When POST is used, the
parameters can be passed to functions either as multipart/form-data or as JSON.

API key can be sent in request parameters, session (if user is logged in) or in
HTTP **X-Auth-Key** header.

Standard API responses
~~~~~~~~~~~~~~~~~~~~~~

**Standard responses in status/body:**

* **200 OK** *{ "result": "OK" }* API call completed successfully.

**Standard error responses in status:**

* **403 Forbidden** the API key has no access to this function or resource
* **404 Not Found** method or resource doesn't exist
* **500 API Error** API function execution has been failed. Check
  input parameters and server logs.

In case API function failed to execute but server returned normal response, API
error response will contain JSON data with *_log* property. In case of errors
it is filled with server warning and error messages:

.. code-block:: json

    {
        "_log": {
            "40": [
                "unable to add object, already present",
            ]
        },
        "result": "ERROR"
    }

RESTful API
-----------

Majority EVA ICS API components and items support `REST
<https://en.wikipedia.org/wiki/Representational_state_transfer>`_. Parameters
for *POST, PUT, PATCH* and *DELETE* requests can be sent in both JSON and
multipart/form-data. For JSON, *Content-Type: application/json* header must be
specified.

RESTful API responses
~~~~~~~~~~~~~~~~~~~~~~

**Success responses:**

* **200 OK** API call completed successfully
* **201 Created** API call completed successfully, Response header *Location*
  contains uri to the newly created object
* **204 No Content** API call completed successfully, no content to return

**Error error responses:**

* **403 Forbidden** the API key has no access to this function or resource
* **404 Not Found** method or resource doesn't exist
* **500 API Error** API function execution has been failed. Check
  input parameters and server logs.

Response body may contain additional information encoded in JSON.

JSON RPC
--------

Additionally, API supports `JSON RPC 2.0
<https://www.jsonrpc.org/specification>`_ protocol. JSON RPC doesn't support
sessions, so user authorization is not possible. Also note that default JSON
RPC result is *{ "ok": true }* (instead of *{ "result": "OK" }*). There's no
error result, as JSON RPC sends errors in "error" field.

JSON RPC API URL for SYS API is:

    **\http://<ip_address:port>/sys-api**

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

**RESTful:**

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/test.rest
    :response: http-examples/sysapi/test.resp

.. _sysapi_save:

save - save database and runtime configuration
----------------------------------------------

All modified items, their status, and configuration will be written to the disk. If **exec_before_save** command is defined in the controller's configuration file, it's called before saving and **exec_after_save** after (e.g. to switch the partition to write mode and back to read-only).

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/save.req
    :response: http-examples/sysapi/save.resp

Parameters:

* **k** API key with *sysfunc=yes* permissions

**RESTful:**

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/save.rest
    :response: http-examples/sysapi/save.resp-rest

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

**RESTful:**

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/cmd.rest
    :response: http-examples/sysapi/cmd.resp

.. _sysapi_set_debug:

set_debug - switch debugging mode
---------------------------------

Enables and disables debugging mode while the controller is running. After the controller is restarted, this parameter is lost and controller switches back to the mode specified in the configuration file.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/set_debug.req
    :response: http-examples/sysapi/set_debug.resp

Parameters:

* **k** API key with *master* permissions
* **debug** 1 for enabling debug mode, 0 for disabling

**RESTful:**

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/set_debug.rest
    :response: http-examples/sysapi/set_debug.resp-rest


.. _sysapi_cat_lock:

Locking functions
=================

.. _sysapi_lock:

lock - lock token request
-------------------------

Lock tokens can be used similarly to file locking by the specific process. The difference is that SYS API tokens can be:

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

* **t** maximum time (seconds) to get token
* **e** time after which token is automatically unlocked (if absent, token may be unlocked only via unlock function)

**RESTful:**

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/lock.rest
    :response: http-examples/sysapi/lock.resp-rest

.. _sysapi_unlock:

unlock - release lock token
---------------------------

Releases the previously obtained lock token.

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/unlock.req
    :response: http-examples/sysapi/unlock.resp

Parameters:

* **k** API key with *allow=lock* permissions
* **l** lock id

Returns:

In case token is already unlocked, *remark = "notlocked"* note will be present in the result.

**RESTful:**

..  http:example:: curl wget httpie python-requests
    :request: http-examples/sysapi/unlock.rest
    :response: http-examples/sysapi/unlock.resp

