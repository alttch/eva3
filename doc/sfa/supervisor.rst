Supervisors
***********

Starting from 3.3.1 :doc:`/sfa/sfa/` API keys can have a special permission
*allow=supervisor*, which provides the following features:

API locks
=========

Supervisor can use :doc:`/sfa/sfa_api` to set supervisor lock and switch the
server API in read-only mode. In read-only mode SFA API denies an access to
functions, which modify item states (unit actions, set/reset/clear/toggle for
lvars, macro run etc.) except caller is in the lock scope.

When supervisor lock is set, API function *test* returns field
*supervisor_lock* with lock information. When there is no lock set,
*supervisor_lock* field is *null*.

Supervisor lock can be cleared by any user, which is in the unlock scope. There
is also not necessary clearing existing lock to set the new one - if user or
API key is in the unlock scope, the lock can be overriden.

Both lock and unlock scopes can be:

* **null** any supervisor can pass
* **k** only supervisors with the same API key as the lock owner has
* **u** only lock-owning user

To set user scope ("u"), API call must be performed with valid user token. Lock
owner is set automatically using API call access data (key / user). Users with
master key can override lock owner, setting lock user and key ID to any values.

.. note::

    Users with master key are not affected with supervisor locks in any way and
    can pass / unlock them without any restrictions.

As soon as supervisor lock is set, :ref:`js_framework` receives an event
*supervisor.lock* with lock information dict as the function argument and a
message or informational popup can be displayed for logged in users.

When supervisor lock is cleared, :ref:`js_framework` receives an event
*supervisor.unlock*.

Broadcast messages
==================

Supervisor can send broadcast message to all logged in users. The message is
received by :ref:`js_framework` with event *supervisor_message* and the
following dictionary structure as the function argument:

* **sender** message sender

  * **key_id** sender API key ID
  * **u** sender user

* **text** message text

Users with master key can override message sender.

CLI
===

All supervisor methods can be also executed from the command line. See "eva sfa
supervisor" command for more details.
