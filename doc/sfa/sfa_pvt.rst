SFA PVT
*******

While developing the interfaces for :doc:`/sfa/sfa` you face the issue of the
private data protection: the UI is loaded with the javascript application that
runs in the browser and requires authentication to access the
:doc:`/sfa/sfa_api` functions. However, the application may contain components
which an unauthorized user should not see: plans of the building, security cam
footages, even the list of the managed :doc:`items</items>` may be
confidential.

One way to solve this problem is to use the frontend server for such content.
However, frontend is not always necessary and, in our case, the content
structure often requires the access rights to certain parts to be set on the
front-end. Therefore, it may involve duplicating user base and difficult
integration of the additional authentication methods.

In most cases, it would be sufficient to delineate access to such content with
the help of SFA PVT server. The access rights to the certain files and catalogs
are regulated with **pvt** parameter of API key.

The PVT server interface is available at *http(s)://<IP_address_SFA:Port>/pvt*,
and the private content should be placed in **pvt** folder of EVA root
directory.

**pvt** parameter of API keys supports :ref:`MQTT<mqtt_>`-style wildcards,
i.e.:

.. code-block:: ini

    pvt = map.jpg, c1/#, +/content.js

will give the key access to *map.jpg*, all files and subfolders of *c1* folder
as well as *content.js* file in any first-level folder.

If the client is authenticated in advance, the future requests do not require
*k=APIKEY* param.

.. contents::

Loading files from PVT Server
=============================

The file can be loaded with the following request:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=FILE

    or

    http(s)://<IP_address_SFA:Port>/pvt/FILE?k=APIKEY

where

* **k** valid API key
* **f** a full relative file path, i.e. *map.jpg* or *c2/content.js*

Receiving the file list
=======================

Use **c=list** request param to receive the file list by the specified mask:

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=FILEMASK&c=list

The mask should be included in the pvt key access right parameter, for example

.. code-block:: ini

    pvt = c1/*.json ; or c1/# for all files and masks

The complete request example:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=c1/*.png&c=list

which return JSON array:

.. code-block:: json

   [{
        "name": "1.png",
        "size": 2443,
        "time": {
            "c": 1507735364.2441583,
            "m": 1507734605.1451921
        }
    },
    {
        "name": "2.png",
        "size": 2231,
        "time": {
            "c": 1507735366.5561802,
            "m": 1507735342.923956
        }
    }] 

where

* **size** file size (in bytes)
* **time/c** inode creation time (ctime, UNIX timestamp)
* **time/m** file modification time (mtime)

Receiving the newest and the oldest file
========================================

Use **c=newest** (**c=oldest**) param to do the typical job of the management
interfaces - receiving the newest file from the specified folder.

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=FILEMASK&c=newest

Example: there is a monitoring camera that uploads a file to the folder on the
server every 10 seconds. The uploaded files are named, i.e. TIMESTAMP.jpg or
ID.jpg.

Connect the file with these images to pvt:

.. code-block:: bash

    cd pvt
    ln -sf /path/to/camerafolder cam1

and easily receive the newest file with the following request:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=cam1/*.jpg&c=newest

.. _sfa_pvt_images:

Image Processing
================

Use **ic=resize** to ask the server to preprocess the image file. To let the
server process images, Python PIL (`pillow <https://python-pillow.org/>`_)
library should be installed. :doc:`EVA installer</install>` automatically
installs the library using pip3.

Please, make sure that system has at least **libjpeg-dev** and **libjpeg8-dev**
before EVA setup, otherwise, PIL won't work with JPEG images.

In case you miss this and  server returns an error ("decoder not available"),
reinstall pillow:

.. code-block:: bash

    <EVA_DIR>/venv/bin/pip install --no-cache-dir -I pillow

If everything is installed correctly, you can receive the processed image using
the following request:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=FILE&ic=resize:XxYxQ:encoder

where:

* **X** and **Y** - image maximum width/height
* **Q** image quality
* **encode** image encoder

I.e. let's get an image *pvt/cam/1.jpg*, resize it to 800x600 as max, and
convert to JPEG with 90% quality:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=cam1/1.jpg&ic=resize:800x600x90:jpeg


We may combine **ic** with **c** param, allowing us to receive the newest file
by the mask. The request

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=cam1/*.jpg&c=newest&ic=resize:800x600x50:jpeg

will return the newest jpeg file from cam1 folder having scaled the image size
to max 800x600 (proportionally) and reduced its quality to 50%. If the newest
file cannot be processed (for example, the image isn't completely loaded by cam
yet and the file is locked), the server will attempt to process the previous
one.

If the content is processed immediately before its loading by the interface,
the server won't need to generate the unnecessary images, especially if every
client demands a specific format.

The maximum size of source file for the image processing is 10 megabytes.

Disabling cache
===============

To ensure the request cashing is disabled, add **nocache** parameter with any
value:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/pvt?k=APIKEY&f=FILE&nocache=VALUE

if you use this parameter for requests, web browser will not cache a file (if
random value is used). Besides, the server will set **Cache-Control**,
**Expires** and **Pragma** headers to the values which prohibit any caching.

.. _sfa_pvt_registry:

Serving private data from EVA ICS Registry
==========================================

To serve private structured data from :doc:`EVA ICS registry</registry>`, use
the following request:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/%pvt/REGISTRY-KEY

where REGISTRY-KEY - key name, relative to *eva3/HOST/userdata/pvt*, e.g.
to request a key "eva3/HOST/userdata/pvt/codes/code1" use the following request:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/%pvt/codes/code1

The session key should have permissions either to the whole pvt data ("#") or
to specific registry folders/keys. ACLs for registry keys should start with
"%/", e.g. to grant an access to the above key, pvt ACL should be
"%/codes/code1". Wildcards in paths ("#") are supported.

By default, registry data is served in JSON. To change format or add locale
translation, see :doc:`/sfa/serve_as`.

.. _sfa_rpvt:

Remote content
==============

SFA PVT can act as a proxy, fetching allowed resources in local network and
displaying them to user.

This can be done with request

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/rpvt?k=APIKEY&f=http://remote_host/folder/file&nocache=some_random_value

Param **nocache** is optional. If user is logged in, param **k** can be
omitted.

Example: you have a chart on storage server in local network displaying storage
usage. The chart is located at http://192.168.1.20/charts/zfs.png

Set prvt permissions of API key to:

    192.168.1.20/charts/#

This will grant access to all files on the specified host in /charts/ folder.

Then include remote chart in your interface:

.. code-block:: html

    <img src="/rpvt?k=APIKEY&f=192.168.1.20/charts/zfs.png" />

As you see, the remote client doesn't need to have a direct access to
*192.168.1.20* web server, **/rpvt** API call acts for him as a content proxy.

To use remote content feature, you must follow the rules:

* protocol (http/https) doesn't need to be specified in **rpvt** API key param.

* **f** param of **/rpvt** request may contain uri protocol (e.g.
  *http://192.168.1.20/charts/zfs.png*). If the protocol is not specified, SFA
  uses plain HTTP without SSL.

* You can not specify http(s) port in **f** param of **/rpvt** unless it's also
  specified in **rpvt** API key param.

* **ic** option is used for :ref:`image processing<sfa_pvt_images>`, same as
  for local PVT file.

* Avoid using *rpvt = #*, this will allow **/rpvt** to work as http proxy for
  any local and Internet resource and may open a security hole.
