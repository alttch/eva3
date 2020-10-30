API session tokens
******************

Special API methods **login** and **logout** (present in all EVA ICS APIs,
**/r/token** resource for RESTful) allow to open API session and use
server-generated API token instead of API key.

To enable tokens, set parameter **session_timeout** greater than zero in
*[webapi]* section of controller configuration (enabled in :doc:`SFA</sfa/sfa>`
by default).

Also, API session tokens are required by :ref:`js_framework`, which uses
them to handle interface sessions.

Usage
=====

Token has no restrictions and can be used as usual API key, the only one
difference is that token has expiration time or can be purged by owner
earlier.

:doc:`/sfa/sfa_templates` and :doc:`/sfa/sfa_pvt` methods additionally accept
authentication tokens set in **auth** cookie. After successful login,
:ref:`js_framework` automatically sets this cookie for URI paths */ui*, */pvt*
and */rpvt*.

Expiration
==========

Token will expire and become invalid, if:

* it hasn't been used for a time, longer, than specified *session_timeout*

* the time, passed since token generation is greater than *session_timeout* and
  *session_no_prolong = yes* is set in controller configuration

* API method **logout** (DELETE /r/token for RESTful) was called

* on any API key modification, which is token assigned to

* on any user account modification, whom token is assigned to (if token was
  obtained with user credentials)

* the controller was restarted.
