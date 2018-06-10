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

cmd - run a remote command
--------------------------

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

* **403 Forbidden** the key has no access to this API function
