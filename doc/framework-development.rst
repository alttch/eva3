Framework development HOWTO
***************************

EVA ICS provides `JavaScript Framework
<https://github.com/alttch/eva-js-framework/>`_, which can be used in both web
browsers and Node.js or similar back-end platforms.

However, sometimes it is necessary to develop a framework for unsupported
platform / programming language. This document describes the process and best
practices.

The described approach is common for developing interfaces and custom
applications for all EVA ICS components, however the best practice is to
develop applications for :doc:`/sfa/sfa` only.

.. contents::

Sessions
========

The client SHOULD not use API keys directly. Instead, login / logout mechanism
SHOULD be used and the client SHOULD always use the token, provided with
:ref:`"login"<sysapi_login>` API method for all API calls and web socket
connections.

If the session is dropped, the client SHOULD either try to login again (if user
credentials or API key are stored) or show a login form to the user to obtain
them.

The session is considered to be dropped, when:

* API call fails because of either network error or with "access denied"
  response code (3).

* The server fails to respond on heartbeat within the required interval.

* The user asks the application to perform logout procedure.

API calls
=========

API calls are performed via EVA ICS API, the client SHOULD use session tokens
to authenticate itself.

Usually, it is a good practice to perform short API calls, without using "wait"
API method parameter. For actions, API call results can be obtained later,
using action UUID.

If a long API call still need to be performed, do not forget to increase client
timeout.

Starting from EVA ICS 3.3.2, it is highly recommended to use JSON RPC API calls
only.

Web socket sessions
===================

A web socket session can be opened by connecting web socket client to:

    \http(s)://CONTROLLER_IP:PORT/ws?k=KEY

where KEY is either API key (not recommended) or a session token (preferred).

Web socket sessions are used to:

* obtain changed states of :doc:`control and monitoring items<items>` without
  performing additional API calls

* receive special server events

The best practice is to use BOTH API calls and web socket events, to let
different event replication methods protect and control each other.

Item events
-----------

The client can subscribe to item events by sending the following JSON frame to
the web socket:

.. code:: json

    {
        "s": "state",
        "g": ["array_of_item_groups"],
        "tp": ["array_of_item_types"],
        "i": ["array_of_individual_item_ids"]
    }

To subscribe the client to events from all items, use the following frame:

.. code:: json

    {
        "s": "state",
        "g": "#",
        "tp": "#"
    }

JSON-serialized item events are received in the format, equal to
:ref:`state<sfapi_state>` API function:

.. code:: json

    {
        "s": "state",
        "d": "<serialized_item_state>"
    }

The client MUST be able to process serialized item states ("d" field) both as a
single event (dict) or as a group of events (array of dicts).

The client MUST send a subscribe frame every time a new web socket is
connected. If another subscribe frame is sent later during the session, it
overrides the previous one.

Log events
----------

The client can subscribe to server log events by sending the following JSON
frame to a web socket (requires either master key or "sysfunc" key permission):

.. code:: json

    {
        "s": "log",
        "l": 20
    }

where "l" is the desired minimal log message level (10=DEBUG, 20=INFO,
30=WARNING, 40=ERROR, 50=CRITICAL)

A log event looks like:

.. code:: json

    {
        "s": "log",
        "d":
            [{
                "dt": "2021-04-13T17:22:12.813938+00:00",
                "h": "eva-hostname",
                "l": 20,
                "lvl": "info",
                "mod": "remote_controller",
                "msg": "lm/eva-x-node2 time diff is 0.001640 sec",
                "p": "sfa",
                "t": 1618334532.8139384,
                "th": "supervisor_default_pool_1"
            }]
    }

The client MUST be able to process serialized log events ("d" field) both as a
single event (dict) or as a group of events (array of dicts).

The client MUST send subscribe frame every time a new web socket is connected.
If another subscribe frame is sent later during the session, it overrides the
previous one.

Special server events
---------------------

The special server events are automatically sent to all clients with web socket
sessions opened. The client MUST either process events or ignore them.

A server event looks like:

.. code:: json
    
    {
        "s": "<event_subject>",
        "d": "<event_data_field>"
    }

The table of server events:

================== ======= ============================================
"s"                "d"        Description
================== ======= ============================================
reload             asap    Server asks clients to reload the interface
server             restart Server is being restarted
server             <EVENT> Other custom server events (reserved)
supervisor.lock    *       A supervisor user performs exclusive-lock
supervisor.message *       A broadcast message from supervisor user
supervisor.unlock          A supervisor user leaves exclusive mode
================== ======= ============================================

Supervisor lock events contain the following block in "d" field:

.. code:: json

    {
        "s": "supervisor.lock",
        "d": {
            "o": {
                "u": "<supervisor_user_name>",
                "utp": "<supervisor_user_type>",
                "key_id": "<supervisor_API_key_id>"
            },
            "l": "<lock_scope>",
            "c": "<unlock_and_override_scope>"
        }
    }

Where scopes are:

* **null** any supervisor can pass the scope
* **k** any user with the same API key can pass the scope
* **u** only the lock owner can pass the scope

Supervisor message events contain the following block in "d" field:

.. code:: json

    {
        "s": "supervisor.lock",
        "d": {
            "sender": {
                "u": "<supervisor_user_name>",
                "key_id": "<supervisor_API_key_id>"
            },
            "text": "<message_text>",
        }
    }

Web socket heartbeat
--------------------

The client MUST send JSON ping-frame every N seconds, where N is less or equal
to :doc:`/sfa/sfa` default server timeout (default: 5 seconds). If the server
does not receive a heartbeat frame from the client within the timeout interval,
it may drop the web socket session.

To notify the server, the client sends the following frame:

.. code:: json

    {
        "s": "ping"
    }

and the server responds with the following frame:

.. code:: json

    {
        "s": "pong"
    }

If the response from the server is not received within the desired client
timeout interval, the client SHOULD consider the web socket session is dropped
and perform the reconnect.

Global heartbeat
================

It is a good practice to use API calls for both :ref:`"test"<sysapi_test>` and
:ref:`"state"<sfapi_state>` methods to obtain both current server and item
states.

If the server does not respond to any method within the client timeout interval
or API method returns an error, the client SHOULD consider the session is
dropped and perform re-login to obtain a new API token.

.. note::

    There is a special parameter "icvars=1" for "test" API method of
    :doc:`/sfa/sfa`, which allows to receive all custom variables from the
    server variables as well.

Item state replication
======================

Basics
------

The client SHOULD use both pull (via "state" API method) and push (via web
socket session) to replicate item states from the server.

For :doc:`/sfa/sfa`, a special API method "state_all" may be used to obtain
states of all desired item types within the single API call. The method accepts
the following parameters:

* **k** API key or token
* **p** Item type or array of item types (if null - states are returned for all
  item types)
* **g** Item groups (array, if null - states are returned for all item groups)

State event handling
--------------------

When a push state event or a state data from pull request is processed, it is
better to use the following practice:

* Lock local item state list
* Process new item states one-by-one
* Unlock item state list

Processing of item states
-------------------------

To avoid confusions between push and pull states, the following practice is
recommended:

* If there is no state for an item - accept the incoming state.

* Else, if the state frame "controller_id" field does not match the
  "controller_id" field of the stored item state - accept the incoming state
  (happens rarely, when the system administrator decides to move the item from
  one EVA ICS node to another).

* Else, if the state contains "ieid" field (see below) - use it to consider is
  the incoming state newer than existing. If the client has got the stored
  state with newer "ieid" - drop the incoming (or use it as the archived data).

* Else, if the state frame contains "set_time" field - use the state with the
  max "set_time" (not recommended as the primary method, as time on different
  nodes may go backwards). If the client has got the stored state with newer
  "set_time" - drop the incoming (or use it as the archived data).

* If none of the above conditions are met - accept the incoming state.

Using IEID
~~~~~~~~~~

Starting from EVA ICS 3.3.2, item states are replicated between EVA ICS nodes
and between client applications and server back-end with "IEID" (Incremental
Event Identifier). IEID is always incremental and it is the most reliable way
in EVA ICS to handle item state events.

All serialized item states have "ieid" field, which is changed only when either
item state or some special item parameters (e.g. "action_enabled" for units or
"expires" for lvars) are changed.

IEID is always the array of two 64-bit unsigned integer numbers:

* The first number contains the controller boot ID (incremented every time when
  the controller is started)

* The second number contains the system monotonic timer where the controller is
  running (can not go backwards).

So, the best practice to determine is the incoming event newer or older than
the existing one, is:

* If OLD_IEID[0] < NEW_IEID[0] - accept the incoming state.

* Else: if OLD_IEID[0] == NEW_IEID[0] AND OLD_IEID[1] < NEW_IEID[1] - accept
  the incoming state.

* Else: Drop the incoming state or use it as the archived data.

.. note::

    In EVA ICS 3.3.2 IEIDs are not kept between the controller reboots. The new
    IEIDs are generated automatically at every controller startup, which should
    not be confusing, as the main idea of IEID is to prevent push/pull event
    processing conflicts. However, in the versions above 3.3.2, IEIDs are
    permanent for the current states and stored in local state databases,
    unless the node works on read-only mode storage device.

If a controller becomes disconnected, its items have "phantom" IEID states, as
*[0,0]*.

Actions
=======

* :ref:`Unit<unit>` and :doc:`macro</lm/macros>` actions SHOULD be usually
  performed without "w" param to let API call be executed instantly.

* The action state can be obtained later with :ref:`"result"<sfapi_result>` API
  method.

* The client SHOULD consider any action can be failed or refused and keep the
  local item state until the new state event is received from the server.

* The client MAY use units' fields "nstatus" and "nvalue" from received state
  events:

    * If "nstatus" != "status" OR "nvalue" != "value" - the unit is busy and
      executing action, targeting to the next status = "nstatus" and next value
      = "value".
      
    * The interface application can use the above e.g. to block the button
      until the action is finished, unless the unit has action queue enabled
      and the interface has a feature to put new actions into it.

Timers
======

When using :ref:`logical variables<lvar>` as timers, the client SHOULD always
consider the local time may be different from the server time. If a task or an
interface element requires to calculate the time before the lvar expiration,
the following formula may be used (example for JavaScript):

.. code:: javascript

    /* server_time - "time" field in the result of "test" API call
       Timestamp difference is usually re-calculated at every heartbeat,
       the local timestamp is divided by 1000 as JavaScript getTime() function
       returns milliseconds */
    let tsdiff = new Date().getTime() / 1000 - server_time;

    /* Calculate expiration time for a lvar timer
       lvar.expires and lvar.set_time - fields from lvar state event */
    let expires_in = lvar.expires - new Date().getTime() / 1000 + lvar.set_time;
    /* Correct expiration time with tsdiff */
    expires_in += tsdiff;

