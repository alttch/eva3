EVA ICS 3.3.2
*************

What's new
==========

* Core Plugins API v2
* Data pullers
* SSL, TLS and SMTP auth support for LM PLC mailer

Complete change log: https://get.eva-ics.com/3.3.2/stable/CHANGELOG.html

Update instructions
===================

* If core plugins are used, change their config sections to
  [plugin.<pluginname>] in the controllers' ini files.

Note for Python 3.6 users: support of Python 3.6 is very limited, consider
upgrading to 3.7+.

Added / updated 3rd party modules
---------------------------------

The following modules are installed / updated automatically in EVA venv. If
your setup has no Internet connection, install them manually before applying
the update.

.. code-block::

    cachetools==4.1.1
    asciichartpy==1.5.3
