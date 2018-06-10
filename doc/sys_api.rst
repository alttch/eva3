SYS API
=======

SYS API is a common API present in all EVA controllers. SYS API functions are
made to manager controller itself.

SYS API is called through URL request

**\http://<IP_address:Port>/sys-api/function?parameters**

If SSL is allowed in the controller configuration file, you can also use https
calls.

All functions can be called using GET and POST methods. When POST method is
being used, the parameters can be passed to functions eitner as www-form or as
JSON.

.. contents::

.. _s_test:

test - test API/key and get system info
---------------------------------------

Test can be executed with any valid API key of the controller the function is
being called to.

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
------------------------------

Executes a remote :ref:`command script<cmd>` on :doc:`/uc/uc` or :doc:`/lm/lm`.
The API key should be masterkey or have 'allow = cmd' permission.

Parameters:

* **k** valid API key
* **c** name of the command script
* **a** command arguments (passed to the script)
* **w** wait (in seconds) before API call sends a response. This allows to try
        waiting until a command finish
* **t** maximim time of command execution. If the command fails to finish
        within the specified time (in sec), it will be terminated

Returns JSON dict

.. code-block:: json

    {
       "args": [ "<specified>", "<command>", "<parameters>" ],
       "cmd": "<command>",
       "err": "<stderr output>",
       "exitcode": "<script exit code>",
       "out": "<stdout output>",
       "status": "<current_status>",
       "time": {
           "<status1>": UNIX_TIMESTAMP,
           "<status2>": UNIX_TIMESTAMP,
           ........................
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
-------------------------

Lock tokens can be used similarly to file locking by the specific process. The
difference is that SYS API tokens can be:

* centralized for several systems (any EVA server can act as lock server)
* removed from outside
* automatically unlocked after the expiration time, if the initiator failed or
  forgot to release the lock

used to restrict the parallel process starting or the access to system
files/resources.

Important: even if different EVA controllers are are working on the same
server, their lock tokens are stored in different bases. To work with the token
of each subsystem, use SYS API on the respective address/port.

Parameters:

* **k** API key with "sysfunc=yes" permissions
* **l** lock ID (arbitrary)
* **t** maxmum timeout (seconds) to get token (optionally)
* **e** time after which token is automatically unlocked (if absent, token may
        be unlocked only via unlock function)

returns JSON dict { "result": "OK" }, if lock has been received or {
"result": "ERROR" }, if lock failed to be obtained

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_unlock:

unlock - release lock token
---------------------------

Releases the previously requested lock token.

Parameters:

* **k** API key with "sysfunc=yes" permissions
* **l** lock token ID

returns JSON dict { "result" : "OK" }. In case token is already
unlocked, *remark = "notlocked"* note will be present in the result.

Errors:

* **403 Forbidden** the API key has no access to this function
* **404 Not Found** token not found

.. _s_log_rotate:

log_rotate - rotate controller's log file
-----------------------------------------

Rotates log file similarly to kill -HUP <controller_id>


Parameters:

* **k** API key with "sysfunc=yes" permissions

returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_log:

log_debug, log_info, log_warning, log_error, log_critical - write to the log
----------------------------------------------------------------------------

The external application can put the message in the logs on behalf of the
controller.

Parameters:

* **k** API key with "sysfunc=yes" permissions
* **m** message to log

returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_log_get:

log_get - get log records
-------------------------

This command allows to read the log records from the controller. Log records
are stored in the controllers' memory until restart or the time
(*keep_logmem*), specified in controller configuration passes.

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
---------------------------------

Enables and disables debugging mode while the controller is running. After the
controller is restarted, this parameter is lost and controller switchs back to
the mode specified in the configuration file.

Parameters:

* **k** API key with "sysfunc=yes" permissions
* **debug** 1 for enabling debug mode, 0 for disabling

returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function

.. _s_get_cvar:

get_cvar - get variable
-----------------------

Returns one or all user-defined variables.

Important: even if different EVA controllers are are working on the same
server, they have different sets of variables To set the variables for each
subsystem, use SYS API on the respective address/port.

Parameters:

* **k** API key with masterkey permissions
* **i** variable name (if not specified, all variables will be returned)

Returns JSON dict

.. code-block:: json

    {
        "VARIABLE" = "VALUE"
    }

Errors:

* **403 Forbidden** the API key has no access to this function
* **404 Not Found** the specified variable is not defined

.. _s_set_cvar:

set_cvar - set variable value
-----------------------------

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
----------------------------------------------

All modified items, their status, and configuration will be written to the
disk. *exec_before_save* command defined in the controller's configuration file
is called before recording and *exec_after_save* after (i.e. to switch the
partition to write mode and back to read-only).

Parameters:

* **k** API key with "sysfunc=yes" permissions

returns JSON dict { "result" type: "OK" }

Errors:

* **403 Forbidden** the API key has no access to this function


