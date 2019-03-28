SFA Templates
*************

:doc:`/sfa/sfa` uses `jinja2 <http://jinja.pocoo.org/>`_ template engine to
serve server-side templates. You can use SFA templates for regular HTML,
javascript and JSON data files. Both *ui* and *pvt* folders can contain
template files, the difference is only that templates in *ui* are public while
templates in *pvt* are served via :doc:`SFA PVT<sfa_pvt>`.

Template files
==============

All files with *.j2* extension are processed as templates, *index.j2* has more
priority than *index.html* as the primary interface page.

Templates support all `jinja2 <http://jinja.pocoo.org/>`_ functions and
features, plus have some specific built-in variables and functions.

Template variables
==================

The following variables are available in all templates:

* All :ref:`custom user-defined variables<sfa_cvars>`

* **server** contains a dict with a system and current API key info (equal to
  SYS API :ref:`test<sysapi_test>` function result) plus an additional key
  **remote_ip** which contains either request IP address or value of
  *X-Real-IP* variable (if set by frontend server).

* **request** contains `CherryPy request
  object<https://tools.ietf.org/doc/python-cherrypy3/api/cherrypy._cprequest.Request-class.html>`_.
  (e.g. to output user agent, use *{{ request.headers.get('User-Agent') }}*)

Template functions
==================

All templates have the following built-in functions:

groups
------

Get list of item groups

.. code-block:: python

    groups(g=None, p=None, k=None)

where:

* **g** filter by group (use :ref:`MQTT-style<mqtt_>` wildcards)

* **p** item type (*U* for :ref:`unit<unit>`, *S* for :ref:`sensor<sensor>`,
  *LV* for :ref:`lvar<lvar>`), required

* **k** :ref:`API key<sfa_apikey>` (use key ID instead of key itself)

The function is similar to SFA API :ref:`groups<sfapi_groups>` except that if
API key is not specified, the current key is used.

state
-----

Get list of items and their state

.. code-block:: python

    state(i=None, g=None, p=None, k=None):

where:

* **i** full item id (*group/id*), optional

* **g** filter by group (use :ref:`MQTT-style<mqtt_>` wildcards)

* **p** item type (*U* for :ref:`unit<unit>`, *S* for :ref:`sensor<sensor>`,
  *LV* for :ref:`lvar<lvar>`), required

* **k** :ref:`API key<sfa_apikey>` (use key ID instead of key itself)

The function is similar to SFA API :ref:`state<sfapi_state>` except that if API
key is not specified, the current key is used.

