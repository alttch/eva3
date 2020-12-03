HMI file uploads
****************

:doc:`/sfa/sfa` has a special HTTP method to handle uploads.

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/upload

The method accepts standard multipart-form data requests and processes them with
:doc:`/lm/macros`.

.. contents::

File upload form
================

How does it work
----------------

An upload form can be either standard HTML web-form or AJAX-based. Here is an
example of the standard one:

.. code:: html

    <form action="/upload" method="POST" enctype="multipart/form-data">
        Select file to upload:
        <input type="file" name="ufile">
        <input type="hidden" name="rdr" value="/ui/upload_example.html">
        <input type="hidden" name="process_macro_id" value="tests/upload_handler">
        <input type="submit" value="Upload file" name="submit">
    </form>

What happens, when a file is uploaded and the method is called:

* The form parameters are checked ("ufile" and "process_macro_id" are mandatory)
* If there is a file to upload chosen, the macro with id, specified in
  "process_macro_id" is called.
* If there is "rdr" form parameter set, the method performs redirect to the
  specified URI
* Otherwise, the method returns JSON output of macro execution result:

.. code:: json

    {
        "args": [],
        "err": "",
        "exitcode": 0,
        "finished": true,
        "finished_in": 0.0034916,
        "item_group": "nogroup",
        "item_id": "m1",
        "item_oid": "lmacro:nogroup/m1",
        "item_type": "lmacro",
        "kwargs": {
            "content": "<binary>",
            "data": {
                "aci": {
                    "id": "6d7dca71-865b-4aac-8f1d-5c4f4a979c68",
                    "key_id": "masterkey"
                },
                "content_type": "image/jpeg",
                "file_name": "wpbig.jpg",
                "form": {
                    "submit": "OK"
                },
                "sha256": "0393e47ec35f73e12d333bb719d30e3959bd140bf952c69b4139b956957a8c4c",
                "system_name": "sfa/lab-ws2"
            }
        },
        "out": "",
        "priority": 100,
        "status": "completed",
        "time": {
            "completed": 1607025058.628277,
            "created": 1607025058.6247854,
            "pending": 1607025058.6249535,
            "queued": 1607025058.625362,
            "running": 1607025058.6257577
        },
        "uuid": "19a71537-cfea-4154-b1f4-dc0897216abe"
    }

Errors
------

* 400 (Bad Request) - invalid HTTP request or "ufile" or "process_macro_id"
  parameters are not set

* 404 (Not Found) - the macro with the specified id is not found
* 403 (Forbidden) - the user has no access to the requested macro
* 500 (API Error) - all other errors

In case if the file is not specified and "rdr" param is not set, the method
returns:

.. code:: json

    { "ok": false }

Additional form parameters
--------------------------

* **k** API key (set automatically by `EVA ICS Framework
  <https://github.com/alttch/eva-js-framework>`_ version 0.3.9 or above)

* **w** seconds to wait until macro execution is completed

* **p**: macro queue priority (default is 100, lower is better)

* **q** global queue timeout, if expires, action is marked as "dead"


* all other parameters are sent to macro as a dict *data["form"]*

Processing macro
================

When the file upload is complete, :doc:`Logic macro </lm/macros>` is being
called, so the content is actually transferred for processing to the
:doc:`/lm/lm` where the macro is located.

The macro automatically gets these parameters:

* **content** content of the uploaded file (binary)
* **data** upload information data:

    * **aci** API call info dict
    * **content_type** file content type, reported by client
    * **file_name** file name, reported by client
    * **form** the dict of all additional upload form parameters
    * **sha256** SHA256-checksum of the uploaded file (calculated by SFA)
    * **system_name** system name, the file is coming from

Here's an example of the very simple macro, which stores uploaded files in /tmp:

.. code:: python

    print(f'uploading file {data["file_name"]}')
    assert data['sha256'] == sha256sum(content)
    with open('/tmp/' + data['file_name'], 'wb') as fh:
        fh.write(content)
        out = 'upload completed'


Security and file upload limits
===============================

* To upload files, the user should have an access to the corresponding processing macro

* There's no built-in limitations for uploaded file size, but the limit can be
  set using :ref:`SFA HTTP front-end <install_frontend>`.
