Enterprise extensions
*********************

.. contents::

EVA JS Framework WASM extension
===============================

`WASM <https://webassembly.org>`_ extension for `EVA JS Framework
<https://github.com/alttch/eva-js-framework/>`_ offloads state processing from
the web browser JavaScript engine to the WASM application, allowing SCADA HMI
to monitor hundreds of items without a client device overhead.

Installation
------------

* Obtain WASM extension from a `EVA ICS representative
  <https://www.eva-ics.com/contacts>`_.

* The extension requires EVA JS Framework version 0.3.25 or above.

* Unpack *evajw-XXXX.tgz* archive into the directory where EVA JS Framework is
  installed. E.g. if the framework is installed in */opt/eva/ui*, the module
  should be placed in */opt/eva/ui/evajw*.

* Put the following code in your HMI, before starting the web-HMI application
  or EVA JS Framework:

.. code:: javascript

    $eva.wasm = true;

* The WASM module will be automatically loaded at framework start.

* If the module is not available, the error message will be displayed in the
  JavaScript development console, as well in the web browser and HMI will be
  stopped.

* If the module license is not valid for the current domain or expired, the
  error message will be displayed in JavaScript development console and the
  framework will automatically switch itself to the regular mode.

* If the license expires within a month or already expired, the module displays
  an alert.

* To make sure the WASM module works fine, enable debug mode in EVA JS
  Framework:

.. code:: javascript

    $eva.debug = true;

* When debug mode is enabled, events processed by the WASM extension are
  prefixed with "W" (e.g. *EVA::Wws state* instead of a regular *EVA::ws
  state*).

Licensing
---------

* The WASM extension is licensed for the specified customers' domains and can
  not be used on others. If a user requires accessing web-HMI via IP address,
  it should be added in the license as well.

* The license is built-in into the copy of the WASM extension, owned by the
  customer.

* The license may have expiration time or be unlimited.

* To check the license expiration time manually, the following function can be
  used:

.. code:: javascript

    evajw.get_license_expiration(); // returns either null or the licnese
                                    // expiration timestamp

* The list of domains/IP addresses is encrypted and can not be read.

Limitations
-----------

* The WASM extension does not support calling the *unwatch* method for the
  particular handler function. Watch can be cleared by *oid* or globally only.

* OID masks do not support internal wildcards (e.g. "sensor:*/test")
