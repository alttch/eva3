API Clients
***********

All EVA API servers were designed as a simple and user-friendly way to work
from a command line using traditional calling methods of Linux http requests:
GET, wget, lynx, curl etc. That is why JSON incoming data is always duplicated
with the traditional GET/POST request parameters.

API outgoing data is always in JSON format, which can easily be parsed with
the use of `jq <https://stedolan.github.io/jq/>`_ (usually available in all
modern Linux distributions), for example:

.. code-block:: bash

    curl -s 'http://localhost:8812/jrpc?i=1&m=test&p=%7B%22k%22%3A%22APIKEY%22%7D' |jq -r .result.version

You may call API functions via HTTP GET or HTTP POST - all functions respond
similarly regardless of the request method. You may use www-form as well as
JSON for POST.

If you want to integrate EVA API in your Python or PHP application, EVA can
offer ready-made client libraries.

.. contents::

.. _js_framework:

EVA JS Framework
================

`EVA JS Framework <https://www.npmjs.com/package/@eva-ics/framework>`_ and `EVA
JS Toolbox <https://www.npmjs.com/package/@eva-ics/toolbox>`_ are used to build
web browser interfaces with HTML and JavaScript.

Framework can be also used in `Node.js <https://nodejs.org/>`_ apps.

.. note::

    Starting from EVA ICS 3.2.3 JavaScript Framework is not installed by
    default. Previous EVA SFA Framework is deprecated and no longer supported.

Framework requires **fetch** function, which is available in all modern
web browsers. For old browsers, a polyfill must be used, `unfetch
<https://github.com/developit/unfetch>`_ is the recommended one.

API client for Python
=====================

API client for Python has already been installed on all EVA servers and is
used by the system itself. If you want to use the client module on another
system, just create **eva/client** folder, copy **lib/eva/client/apiclient.py**
file into it and create an empty file **__init__.py**. Other files in this
folder are used by the system for a higher level of access to API, which is not
publicly documented.

Example of working with API from Python is located in **include/python/**
folder of EVA.

API classes for Python
----------------------

API has two classes:

.. code-block:: python

    eva.client.apiclient.APIClient()

and

.. code-block:: python

    eva.client.apiclient.APIClientLocal(product, dir_eva=None)

**APIClientLocal** class may be used on the servers where EVA is installed.
When specifying **product='<subsystem code>'** parameter (e.g. *product =
'uc'*) API is automatically initialized by loading parameters and keys
specifically from configuration files of the controller. If you load the
**apiclient.py** module from **lib/eva/client/** folder, it is not necessary to
set **dir_eva** parameter. Otherwise, it should point to EVA root folder.

**APIClient** class should always be initialized manually.

API requires `jsonpickle <https://jsonpickle.github.io/>`_ and `requests
<http://docs.python-requests.org/en/master/>`_ modules.

API initialization
------------------

API is initialized with the use of the following functions:

* **set_key(key)** set API key.
* **set_uri(uri)** set the root API URI (i.e., \http://localhost:8812). You
  don't need to specify the full path to API.
* **set_timeout(timeout)** set maximum request timeout (seconds), 5 seconds by
  default.
* **set_product(product)** set controller type: *uc* for :doc:`/uc/uc`, *lm*
  for :doc:`/lm/lm`, *sfa* for :doc:`/sfa/sfa`. The client automatically
  identifies which API is to be called - either :doc:`/sysapi` one or the one
  of the certain controller  - that is why this parameter is required.
* **ssl_verify(v)** to verify or not SSL certificate validity while working
  through https://. Can be *True* (check) or *False* (don't check). The
  certificate is verified by default.

Example:

.. code-block:: python

    from eva.client.apiclient import APIClient
    api = APIClient()
    api.set_key(APIKEY)
    api.set_uri('http://192.168.0.77:8812')
    api.set_product('uc')

API function call
-----------------

API functions are invoked by calling the **call** function:

.. code-block:: python

    APIClient.call(func, params=None, timeout=None)

where:

* **params** the dict of the request parameters (if required)
* **timeout** - maximum time (in seconds) to wait for the API response (if not
  set - the default timeout is used or the one set during API client
  initialization).

Example:

.. code-block:: python

    from eva.client.apiclient import APIClientLocal
    api = APIClientLocal('uc')
    code, result = api.call('state', { 'i': 'unit1' })

The function returns a tuple of two variables:

* *code* API call result
* *result* the result itself (JSON response converted to Python dict or array).

API result codes
----------------

Result codes are stored in module variables (i.e. **apiclient.result_ok**)

.. code-block:: python

    # the call succeeded
    result_ok = 0
    # the item or resource is not found
    result_not_found = 1
    # access is denied with the set API key
    result_forbidden = 2
    # server responded with error http status (e.g. API function crashed)
    result_api_error = 3
    # unknown error: all errors not listed here fall within this category
    result_unknown_error = 4
    # API is not initialized - URI is not set
    result_not_ready = 5
    # Attempt to call undefined API function
    result_func_unknown = 6
    # server connection failed
    result_server_error = 7
    # the server request exceeded the time set in timeout
    result_server_timeout = 8
    # API response cannot be parsed or is invalid
    result_bad_data = 9
    # API function failed
    result_func_failed = 10
    # API function is called with invalid params
    result_invalid_params = 11
    # API function attempted to create resource which already exists and can't
    # be recreated until deleted/removed
    result_invalid_params = 12
    # the resource is busy (in use) and can not be accessed/recreated or
    # deleted at this moment
    result_busy = 13
    # the method is not implemented in/for requested resource
    result_not_implemented = 14
    # the token, used for API call, is valid, but currently restricted
    result_token_restricted = 15

In case of error, result is an empty dict or contains field "error" which is
filled with error message from server (if available).

.. json_rpc_client_:

JSON RPC API client
===================

As EVA ICS uses standard `JSON RPC 2.0 protocol
<https://www.jsonrpc.org/specification>`_, any 3rd party JSON RPC client may be
used. In the example below, we'll use simple `JSON RPC client for Python 3
<https://github.com/bcb/jsonrpcclient>`_.

Installing
----------

Install Python 3 module:

.. code-block:: bash

    pip3 install jsonrpcclient

Usage example
-------------

Let's call :doc:`/uc/uc_api` method **state** and obtain state of sensors:

.. code-block:: python

    from jsonrpcclient import request as rpc

    r = rpc('http://localhost:8812/jrpc', 'state', k='YOUR_API_KEY', p='sensor')
    for s in r.data.result:
        print(s['oid'])

.. note::

    If using custom API client, you may still put API key to *X-Auth-Key*
    request header. This is against JSON RPC standard, so if you want to keep
    it right, you must have *k* in params in each request.

API result codes
----------------

JSON RPC API responds in the standard JSON RPC way with HTTP code *200 (OK)*.
In case JSON RPC request has no **id**, no body is returned and HTTP response
code is *202 (Accepted)*.

In case of API method errors, HTTP code is still *200 (OK)*. Error codes can be
found in the response body.
