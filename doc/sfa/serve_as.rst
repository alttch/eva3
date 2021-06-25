Serving structured data
***********************

.. contents::

Structured data (YAML and JSON files) is very typical for UI development to
keep settings, texts and other structured information.

EVA ICS provides a feature, called "serve as", which allows to convert any
structured data file on-the-flow and load it into UI applications in the most
convenient way.

This feature is supported by both public UI ("/ui" URLs) and
:doc:`/sfa/sfa_pvt` and enabled automatically for all files with suffixes
".yml", ".yaml" and ".json".

.. _serve_as_format:

Format conversion
=================

To convert a structured file into another format, request it as:

    /ui/filename.yml?as=FMT

where FMT:

* **yml** (or yaml) - convert the file into YAML
* **json** - convert the file into JSON
* **js** - convert the file into JavaScript (requires either "var" or "func" as
  the additional parameter)

e.g. let's convert YAML, which is usually more human-editable and preferred to
keep configs, into JSON:

    /ui/filename.yml?as=json

The file can also be converted on-the-flow to JavaScript variable, or, as
copying JavaScript arrays and dicts is usually tricky, into the function, which
returns the structured data on every call:

    /ui/filename.yml?as=js&func=myfunc

.. _serve_as_locale:

Multi-language
==============

Usage
-----

An additional argument "lang" can be used to apply the chosen locale on **all**
string fields of structured data file. Multi-line strings are processed
correctly, string formatting (left and right white spaces) is preserved:

    /ui/test.yml?as=json&lang=LANG

(as seen from the above example, "lang" can be combined with "as").

Firstly, a locale file should be created. Create a directory
*EVA_DIR/pvt/locales* (used for both UI and :doc:`/sfa/sfa_pvt`). After, create
inside that directory language directories with LC_MESSAGES subdirectory inside
each one. So the tree should look like e.g. ("cs" is for Czech language):

.. code::

    pvt
    └── locales
        └── cs
            └── LC_MESSAGES
                ├── messages.po
                ├── tests
                └────── test.po

".po" files are standard `Gettext <https://en.wikipedia.org/wiki/Gettext>`_
files, which look like:

.. code::

    msgid "this is a test"
    msgstr "je to test"

or e.g. for Japanese (UTF-8):

.. code::

    #, fuzzy
    msgid ""
    msgstr ""
    "Content-Type: text/plain; charset=utf-8\n"

    msgid "this is a test"
    msgstr "これはテストです"

(note that if diacritic is used e.g. in Czech lang messages, the file should
specify UTF-8 encoding as well)

The files can be compiled with "msgfmt" Linux command from "gettext" package
(installed by default by majority Linux distributions):

.. code:: shell

    msgfmt file.po -o file.mo

EVA ICS uses the following strategy to find locale files. E.g. if the document

    /ui/tests/test.yml?as=json&lang=cs

is served, the message files are looked up in the following order:

* EVA_DIR/pvt/locales/cs/LC_MESSAGES/tests/test.mo
* EVA_DIR/pvt/locales/cs/LC_MESSAGES/tests.mo
* EVA_DIR/pvt/locales/cs/LC_MESSAGES/messages.mo

(the last file is the standard common message file). If no message file is
found, the strings are served as-is, without any conversion.

.. note::

    Altrenatively, locale files can be kept in EVA_DIR/ui/locales.
    :doc:`/sfa/sfa` automatically searches for the locale files in "ui" if no
    locale files found in "pvt".

    The option "-o EVA_DIR/ui/locales" for gen-intl can be used to
    automatically generate / compile locale files in EVA_DIR/ui/locales.

Generating
----------

To auto-generate / update ".po" files from JSON or YAML strings, a supplied
tool "gen-intl" can be used (multiple languages can be specified at once):

.. code:: bash

    /opt/eva/bin/gen-intl test.yml -l cs generate

The above command will auto-generate or update "test.po" file and put it to the
corresponding locale path. E.g. if the file absolute path is
*/opt/eva/ui/tests/test.yml*, the result ".po" file will be written to
*/opt/eva/pvt/locales/cs/LC_MESSAGES/tests/test.po*.

After editing, compile ".po" file manually with "msgfmt", or run

.. code:: bash

    /opt/eva/bin/gen-intl test.yml -l cs compile

Locale cache
------------

Message files are cached by EVA ICS gettext library, until the :doc:`/sfa/sfa`
server is restarted.

The cache can be turned off by setting development mode
(*server/development:true*) field of *config/sfa/main*
:doc:`registry</registry>` key

On production, the API method :ref:`clear_lang_cache <sysapi_clear_lang_cache>`
can be used, either by calling it manually or during a :doc:`deployment
</iac>`.

Serving structured data from EVA ICS Registry
=============================================

To serve structured data from :doc:`EVA ICS registry</registry>`, use the
following request:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/%pub/REGISTRY-KEY

where REGISTRY-KEY - key name, relative to *eva3/HOST/userdata/pub*, e.g.
to request a key "eva3/HOST/userdata/pub/settings" use the following request:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/%pub/settings

By default, registry data is served in JSON. To change format or add locale
translation, see :ref:`serve_as_format` and :ref:`serve_as_locale`.

To serve private data, see :ref:`sfa_pvt_registry`.

Why serving structure data from registry is more convenient:

* reliability
* unified data storage
* data schemas
