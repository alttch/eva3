User authorization using login/password
=======================================

Third-party apps may authorize :doc:`users</sysapi>` using login and password
as an alternative for authorization via API key.

login - user authorization
--------------------------

Authorizes user in the system and and opens a new authorized session.  Session
ID is stored in cookie.

Attention! Session is created for all requests to API, even if login is not
used; web-browsers use the same session for the host even if apps are running
on different ports. Therefore, when you use web-apps (even if you use the same
browser to simultaneously access system interfaces or other apps) each
app/interface should be associated with different domains/alias/different host
IP addresses.

Parameters:

* **u** user name
* **p** user password

Returns JSON dict { "result" "OK", "key": "APIKEY_ID" }, if the user is
authorized.

Errors:

* **403 Forbidden** invalid user name / password

logout
------

Finishes the authorized session

Parameters: none

Returns JSON dict { "result" : "OK" }

Errors:

* **403 Forbidden** no session available / session is already finished

