If SSL is allowed in the controller configuration file, you can also use https
calls.

All API functions can be called using GET and POST. When POST is used, the
parameters can be passed to functions either as multipart/form-data or as JSON.

API key can be sent in request parameters, session (if user is logged in) or in
HTTP **X-Auth-Key** header.

RESTful
-------

Majority EVA ICS API components and items support `REST
<https://en.wikipedia.org/wiki/Representational_state_transfer>`_. Parameters
for *POST, PUT, PATCH* and *DELETE* requests can be sent in both JSON and
multipart/form-data. For JSON, *Content-Type: application/json* header must be
specified.

API responses
-------------

Each API response (if result is a dict) contain additional *_log* property. In
case of errors it is filled with server warning and error messages:

.. code-block:: json

    {
        "_log": {
            "40": [
                "unable to load PHI mod nonexisting",
            ]
        },
        "result": "ERROR"
    }

**Standard responses in headers/body:**

* **200 OK** *{ "result": "OK" }* API call completed successfully.
* **200 OK** *{ "result": "ERROR" }* API call has been failed.

**Standard error responses in headers:**

* **403 Forbidden** the API key has no access to this function or resource
* **404 Not Found** method or resource doesn't exist
* **500 API Error** API function execution has been failed. Check
  input parameters and server logs.

JSON RPC
--------

Additionally, each EVA ICS API supports `JSON RPC 2.0
<https://www.jsonrpc.org/specification>`_ protocol. JSON RPC doesn't support
sessions, so user authorization is not possible. Also note that default JSON
RPC result is *{ "ok": true }* (instead of *{ "result": "OK" }*). There's no
error result, as JSON RPC sends errors in "error" field.

