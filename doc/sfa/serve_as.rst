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

Locales
=======

An additional argument "lang" can be used to apply locale on **all** string
fields of structured data file. Multi-line fields are processed correctly,
string format (left and right white spaces) is preserved:

    /ui/test.yml?as=json&lang=cs

(as seen from the example above, "lang" can be combined with "as").

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
also specify UTF-8 encoding as well)

The files can be compiled with "msgfmt" Linux command from "gettext" package
(installed by default by majority Linux distributions):

.. code:: shell

    msgfmt file.po -o file.mo

EVA ICS uses the following strategy to find locale files. E.g. if the document

    /ui/tests/test.yml&as=json&lang=cs

is served, the message files are looked up in the following order:

* EVA_DIR/pvt/locales/cs/LC_MESSAGES/tests/test.mo
* EVA_DIR/pvt/locales/cs/LC_MESSAGES/tests.mo
* EVA_DIR/pvt/locales/cs/LC_MESSAGES/messages.mo

(the last file is the standard common message file). If no message file is
found, the string is served as-is, without any conversion.
