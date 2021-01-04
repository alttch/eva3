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

Field "value" in state and history databases increased to 8192 bytes. To
use new size, manually change column size or stop a controller and drop the
table (will be recreated automatically).

Deprecated
----------

* RESTful and direct API calls. Use JSON RPC only
* Read-only file systems
