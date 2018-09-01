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

    curl -s 'http://localhost:8812/uc-api/test?k=APIKEY' | jq .version -r

You may call API functions via HTTP GET or HTTP POST - all functions respond
similarly regardless of the request method. You may use www-form as well as
JSON for POST.

If you want to integrate EVA API in your Python or PHP application, EVA can
offer ready-made client libraries.

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
When specifying **product='<subsystem code>'** parameter (i.e. *product =
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
  identifies which API is to be called - either :doc:`/sys_api` one or the one
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
    # the item is not found or the function requires a different set of
    # parameters
    result_not_found = 1
    # access is denied with the set key
    result_forbidden = 2
    # - API error, e.g. the string param was used instead of a number
    result_api_error = 3
    # unknown error: all errors not listed here fall within this category
    result_unknown_error = 4
    # API is not initialized - URI is not set
    result_not_ready = 5
    # Attempt to call API function unknown to the client
    result_func_unknown = 6
    # server connection failed
    result_server_error = 7
    # the server request exceeded the time set in timeout
    result_server_timeout = 8
    # API returned data not in JSON or it cannot be parsed
    result_bad_data = 9
    # action failed (e.g., when calling  SYS API cmd or UC API action functions)
    result_func_failed = 10
    # the function is called with invalid params
    result_invalid_params = 11

API client for PHP
==================

API client for PHP has already been installed on all EVA servers. If you want
to use the client library on another system, just copy
**include/php/eva-apiclient.php** file.

Example of working with API from PHP is located in **include/php/**
folder of EVA.

API classes for PHP
----------------------

API has two classes:

.. code-block:: php

    <?php EVA_APIClient(); ?>

and

.. code-block:: php

    <?php EVA_APIClientLocal($product, $dir_eva); ?>

**EVA_APIClientLocal** class may be used on the servers where EVA is installed.
When specifying **product='<subsystem code>'** parameter (i.e. *'uc'*) API is
automatically initialized by loading parameters and keys specifically from
configuration files of the controller. If you load the **eva-apiclient.php**
library from **include/php/** folder, it is not necessary to set **dir_eva**
parameter. Otherwise, it should point to EVA root folder.

**EVA_APIClient** class should always be initialized manually.

API requires PHP extensions `JSON <http://php.net/manual/en/book.json.php>`_
and `cURL <http://php.net/manual/en/book.curl.php>`_.

API initialization
------------------

API is initialized with the use of the following functions:

* **set_key($key)** set API key.
* **set_uri($uri)** set the root API URI (i.e., \http://localhost:8812). You
  don't need to specify the full path to API.
* **set_timeout($timeout)** set maximum request timeout (seconds), 5 seconds by
  default.
* **set_product($product)** set controller type: *uc* for :doc:`/uc/uc`, *lm*
  for :doc:`/lm/lm`, *sfa* for :doc:`/sfa/sfa`. The client automatically
  identifies which API is to be called - either :doc:`/sys_api` one or the one
  of the certain controller  - that is why this parameter is required.
* **ssl_verify($v)** to verify or not SSL certificate validity while working
  through https://. Can be *true* (check) or *false* (don't check). The
  certificate is verified by default.

Example:

.. code-block:: php

    <?php
    include "eva-apiclient.php";
    $api = new EVA_APIClient();
    $api->set_key($APIKEY);
    $api->set_uri('http://192.168.0.77:812');
    $api->set_product('uc');
    ?>

API function call
-----------------

API functions are invoked by calling the **call** function:

.. code-block:: php

    <?php
    EVA_APIClient->call($func, $params=null, $timeout=null);
    ?>

where:

* **$params** the dict of the request parameters (if required)
* **$timeout** - maximum time (in seconds) to wait for the API response (if not
  set - the default timeout is used or the one set during API client
  initialization).

Example:

.. code-block:: php

    <?php
    include "eva-apiclient.php";
    $api = new EVA_APIClientLocal('uc');
    list($code, $result) = $api->call('state', array('i' => 'unit1'));
    ?>

The function returns an array of two variables:

* *0* API call result
* *1* the result itself (JSON response converted to Python dict or array).

API result codes
----------------

Result codes are stored in module variables:

.. code-block:: php

    <?php
    # the call succeeded
    $result_ok = 0;
    # the item is not found or the function requires a different set of
    # parameters
    $result_not_found = 1;
    # access is denied with the set key
    $result_forbidden = 2;
    # - API error, e.g. the string param was used instead of a number
    $result_api_error = 3;
    # unknown error: all errors not listed here fall within this category
    $result_unknown_error = 4;
    # API is not initialized - URI is not set
    $result_not_ready = 5;
    # Attempt to call API function unknown to the client
    $result_func_unknown = 6;
    # server connection failed
    $result_server_error = 7;
    # the server request exceeded the time set in timeout
    $result_server_timeout = 8;
    # API returned data not in JSON or it cannot be parsed
    $result_bad_data = 9;
    # action failed (e.g., when calling  SYS API cmd or UC API action functions)
    $result_func_failed = 10;
    # the function is called with invalid params
    $result_invalid_params = 11;
    ?>
