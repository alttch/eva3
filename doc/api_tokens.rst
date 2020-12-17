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

* on any user account modification, which the token is assigned to (if token
  was obtained with user credentials)

* the controller was restarted.

Read-only mode
==============

The client can ask the server to set read-only mode for the current token, e.g.
after an idle period. This can be performed by calling "set_token_readonly" API
method. Read-only mode can not be set for tokens, assigned to master keys.

In read-only mode, only read-only API calls are accepted, others return
"result_token_restricted"(15) API error.

To exit read-only mode, user must either authenticate again and obtain a new
token or re-use the existing one by calling "login" API method with params
*a=CURRENT_TOKEN* and either "u" and "p" (if token was assigned to user
account) or "k" (if token was assigned directly to API key).
