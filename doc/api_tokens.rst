API session tokens
******************

Special API methods **login** and **logout** (present in all EVA ICS APIs,
**/r/token** resource for RESTful) allow to open API session and use
a server-generated API token instead of API key.

To enable tokens, set the parameter **webapi/session_timeout** to a value
greater than zero (enabled in :doc:`SFA</sfa/sfa>` by default).

Also, API session tokens are required by :ref:`js_framework`, which uses
them to handle interface sessions.

Usage
=====

Tokens have no restrictions and can be used as usual API keys, the only
difference is that tokens have expiration time or can be purged earlier by
the owners.

:doc:`/sfa/sfa_templates` and :doc:`/sfa/sfa_pvt` methods additionally accept
authentication tokens set in **auth** cookie. After successful login,
:ref:`js_framework` automatically sets this cookie for URI paths */ui*, */pvt*
and */rpvt*.

Expiration
==========

Token expires and becomes invalid, if:

* it hasn't been used for the time, longer, than specified *session_timeout*

* the time, passed since token generation is greater than *session_timeout* and
  *webapi/session_no_prolong: true* is set in the controller configuration

* API method **logout** (DELETE /r/token for RESTful) was called

* any modification of API key, which is the token assigned to

* any modification of the user account, which is the token assigned to (if
  token was obtained with the user credentials)

* the controller was restarted.

Read-only mode
==============

The client can ask the server to set read-only mode for the current token, e.g.
after an idle period. This can be performed by calling "set_token_readonly" API
method.

In read-only mode, only read-only API calls are accepted, others return
"result_token_restricted"(15) API error.

To exit read-only mode, the user must either authenticate again and obtain a
new token or re-use the existing one by calling "login" API method with params
*a=CURRENT_TOKEN* and either "u" plus "p" (if the token was assigned to the
user account) or "k" (if the token was assigned directly to API key).
