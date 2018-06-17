SFA Framework
=============

SFA Framework is a component of :doc:`/sfa/sfa` that allows you to quickly
create a web application with EVA interface for a specific configuration.

**ui** folder contains *js/eva_sfa.js* file, namely the framework itself and
**lib/jquery*.js** - `jQuery <https://jquery.com/>`_, necessary for correct
operation. Lib folder also contains `Bootstrap <http://getbootstrap.com/>`_
files often used for web application development.

.. contents::

Framework connection
--------------------

Open the file *ui/index.html* in the editor, connect jQuery and SFA Framework:

.. code-block:: html

    <script src="lib/jquery.min.js"></script>
    <script src="js/eva_sfa.min.js"></script>

Framework variables
-------------------

eva_sfa_login, eva_sfa_password
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following variables contain the user login/password, and are used for the
initial authentication:

.. code-block:: javascript

    eva_sfa_login = '';
    eva_sfa_password = '';

eva_sfa_apikey
~~~~~~~~~~~~~~

Another way is to use the variable

.. code-block:: javascript

    eva_sfa_apikey = null;

in case its value is not NULL, the authentication is done with API key

eva_sfa_cb_login_success, eva_sfa_cb_login_error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following two variables contain functions called when the authentication
either succeeded or failed (**data** parameter is equal to `jQuery post
<https://api.jquery.com/jquery.post/>`_):

.. code-block:: javascript

    eva_sfa_cb_login_success = null;
    eva_sfa_cb_login_error = null;

eva_sfa_heartbeat_interval
~~~~~~~~~~~~~~~~~~~~~~~~~~

The interval for a server ping test (heartbeat)

.. code-block:: javascript

    eva_sfa_heartbeat_interval = 5;

eva_sfa_heartbeat_error
~~~~~~~~~~~~~~~~~~~~~~~

The following function is being automatically called in case of the server
heartbeat error:

.. code-block:: javascript

    eva_sfa_heartbeat_error = eva_sfa_restart;

The function is called with **data** parameter containing HTTP error data, or
without parameter if such data is not available (e. g. the error occurred when
attempting to send data via WebSocket).

eva_sfa_ajax_reload_interval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Interval (seconds) for updating data when framework is in AJAX mode:

.. code-block:: javascript

    eva_sfa_ajax_reload_interval = 2;

eva_sfa_force_reload_interval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The next variable forces ajax updates if if the framework is running in
WebSocket mode. *0* value disables updating via AJAX completely, but it's
recommended to keep some value to be sure the interface has the actual data
even if some websocket events are lost.

.. code-block:: javascript

    eva_sfa_force_reload_interval = 5;

eva_sfa_rule_monitor_interval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Interval (seconds) for updating settings of the :doc:`decision-making matrix
rules</lm/decision_matrix>`. Rule settings are updated via AJAX only.

.. code-block:: javascript

    eva_sfa_rule_monitor_interval = 60;

eva_sfa_server_info
~~~~~~~~~~~~~~~~~~~

The next variable is updated by heartbeat and contains API **test** call
results.  This variable may be used by the application to check whether the
framework has established the connection to the server - if not, the variable
is *null*.

.. code-block:: javascript

    eva_sfa_server_info = null;

eva_sfa_tsdiff
~~~~~~~~~~~~~~

This variable contains the time difference (in seconds) between server and
connected client. The value is updated every time client gets new server info.

.. code-block:: javascript

    eva_sfa_tsdiff = null;

eva_sfa_ws_mode
~~~~~~~~~~~~~~~

This variable sets the framework working mode. If its value is *true*, SFA
framework operates via WebSocket, if false - via AJAX. This value is changed by
:ref:`eva_sfa_init()<sf_init>` which tries to detect is the web browser web
socket compatible.  To change the mode manually, change the variable after the
initial framework initialization.

.. code-block:: javascript

    eva_sfa_ws_mode = true;

eva_sfa_ws_event_handler
~~~~~~~~~~~~~~~~~~~~~~~~

The next variable contains function processing WebSocket data. If the user
declares this function, it should return *true* (in case the data processing is
possible hereafter) or false (if the data has already been processed). The
function is called via **data** parameter with the event data set herein.

.. code-block:: javascript

    eva_sfa_ws_event_handler = null;

.. _sfw_reload:

eva_sfa_reload_handler
~~~~~~~~~~~~~~~~~~~~~~

This variable contains function which's called when :doc:`/sfa/sfa` asks
connected clients to reload the interface. If you want the interface to handle
the reload event, you must define this function.

.. note::

    reload event can be processed only when the framework is in a websocket
    mode

.. code-block:: javascript

    eva_sfa_reload_handler = null;

.. _sf_init:

Initialization, authentication
------------------------------

eva_sfa_init
~~~~~~~~~~~~

To initialize the framework run

.. code-block:: javascript

    eva_sfa_init();

eva_sfa_start
~~~~~~~~~~~~~

To start the framework, run

.. code-block:: javascript

    eva_sfa_start();

that will authorize the user and run the data update and event handling
threads.

eva_sfa_start_rule_monitor
~~~~~~~~~~~~~~~~~~~~~~~~~~

After the initialization succeeds, you may additionally start reloading of the
:doc:`decision rules</lm/decision_matrix>`. The following function is not
called by init/start and you should call it separately:

.. code-block:: javascript

    eva_sfa_start_rule_monitor();

eva_sfa_stop
~~~~~~~~~~~~

To stop the framework, call:

.. code-block:: javascript

    eva_sfa_stop();

Event Handling
--------------

eva_sfa_state
~~~~~~~~~~~~~

To manually get :doc:`item</items>` state, use the function

.. code-block:: javascript

    eva_sfa_state(oid)

where:

* **oid** :doc:`item</items>` id in the following format:
  **type:group/item_id**, i.e. *sensor:env/temperature/temp1*

The function returns **state** object or **undefined** if the item state is
unknown.

eva_sfa_register_update_state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the new data is obtained from the server, the framework may run a
specified functions to handle events. To register such function in the
framework, use
 
.. code-block:: javascript

    eva_sfa_register_update_state(oid, cb);

where:

* **oid** :doc:`item</items>` id in the following format:
  **type:group/item_id**, i.e. *sensor:env/temperature/temp1*
* **cb** function which's called with **state** param containing the new item
  state data (**state.status**, **state.value** etc. equal to the regular state
  :doc:`notification event</notifiers>`.)

eva_sfa_register_rule
~~~~~~~~~~~~~~~~~~~~~

Similarly, you can process the :doc:`decision rules</lm/decision_matrix>`
settings. When rule params are changed, the framework runs the function
registered by

.. code-block:: javascript

    eva_sfa_register_rule(rule_id, cb);

where:

* **rule_id** rule id to monitor
* **cb** function which's called with **props** param containing all the rule
  props (similar to LM API `list_rule_props<lm_list_rule_props>`)

Macro execution and unit management
-----------------------------------

eva_sfa_run
~~~~~~~~~~~

To execute :doc:`macro</lm/macros>`, call the function:

.. code-block:: javascript

    eva_sfa_run(macro_id, args, wait, priority, uuid, cb_success, cb_error);

where **macro_id** - macro id (in a full format, *group/macro_id*) to execute,
other params are equal to LM API :ref:`run<lm_run>` function, and
**cb_success**, **cb_error** - functions called when the access to API is
either succeeded or failed. The functions are called with **data** param which
contains the API response.

eva_sfa_action
~~~~~~~~~~~~~~

To run the :ref:`unit<unit>` action, call the function:

.. code-block:: javascript

    eva_sfa_action(unit_id, nstatus, nvalue, wait, priority, uuid, cb_success,
    cb_error);

Where unit_id - full unit id (*group/id*), other parameters are equal to UC API
:ref:`action<uc_action>`, and **cb_success**, **cb_error** - functions called
when the access to API is either succeeded or failed. The functions are called
with **data** param which contains the API response.

eva_sfa_action_toggle
~~~~~~~~~~~~~~~~~~~~~

In case you want to switch :ref:`unit<unit>` status between *0* and *1*, call:

.. code-block:: javascript

    eva_sfa_action_toggle(unit_id, wait, priority, uuid, cb_success, cb_error);

eva_sfa_result, eva_sfa_result_by_uuid
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To obtain a result of the executed actions, use the functions:

.. code-block:: javascript

    eva_sfa_result(unit_id, g, s, cb_success, cb_error);
    eva_sfa_result_by_uuid(uuid, cb_success, cb_error);

eva_sfa_kill
~~~~~~~~~~~~

Terminate unit action and clean up queued commands:

.. code-block:: javascript

    eva_sfa_kill(unit_id, cb_success, cb_error);

eva_sfa_q_clean
~~~~~~~~~~~~~~~

Clean unit action queue but keep the current action running:

.. code-block:: javascript

    eva_sfa_q_clean(unit_id, cb_success, cb_error);

eva_sfa_terminate, eva_sfa_terminate_by_uuid
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Terminate the current unit action either by unit id, or by action uuid:

.. code-block:: javascript

    eva_sfa_terminate(unit_id, cb_success, cb_error);
    eva_sfa_terminate_by_uuid(uuid, cb_success, cb_error);

Working with logic variables
----------------------------

eva_sfa_set
~~~~~~~~~~~

To set the :ref:`logic variable<lvar>` status, use the function:

.. code-block:: javascript

    eva_sfa_set(lvar_id, value, cb_success, cb_error);

eva_sfa_toggle
~~~~~~~~~~~~~~

To switch lvar value between *0* and *1* use

.. code-block:: javascript

    eva_sfa_toggle(lvar_id, cb_success, cb_error);

eva_sfa_reset
~~~~~~~~~~~~~

To reset lvar when used as a timer or flag:

.. code-block:: javascript

    eva_sfa_reset(lvar_id, cb_success, cb_error);

eva_sfa_clear
~~~~~~~~~~~~~

To clear lvar flag or stop the timer:

.. code-block:: javascript

    eva_sfa_clear(lvar_id, cb_success, cb_error);

eva_sfa_expires_in
~~~~~~~~~~~~~~~~~~

Get timer expiration (in seconds). Allows to :ref:`display
timers<sfw_example_timer>` and interactive progress bars of the production
cycles.

.. code-block:: javascript

    eva_sfa_expires_in(lvar_id);

Returns float number of seconds to timer expiration, or:

* **undefined** if :ref:`lvar<lvar>` is not found, or **eva_sfa_tsdiff** is not
  set yet.
* **null** if lvar has no expiration set

* **-1** if the timer is expired
* **-2** if the timer is disabled (stopped) and has status *0*

Modifying decision rules
------------------------

eva_sfa_set_rule_prop
~~~~~~~~~~~~~~~~~~~~~

To change :doc:`decision rules</lm/decision_matrix>` properties, call:

.. code-block:: javascript

    eva_sfa_set_rule_prop(rule_id, prop, value, save, cb_success, cb_error);

Examples
--------

Examples of the SFA framework usage are provided in ":doc:`/tutorial/tut_ui`"
part of the EVA :doc:`tutorial</tutorial/tutorial>`.

.. _sfw_example_timer:

Timer example
~~~~~~~~~~~~~

The following example shows how to display the timer countdown. The countdown
is updated every 500 ms.

.. code-block:: javascript

    function show_countdown() {
        var t = eva_sfa_expires_in('timers/timer1');
        if (t === undefined || t == null) {
            $('#timer').html('');
        } else {
            if (t == -2) {
                $('#timer').html('STOPPED');
            } else if (t == -1 ) {
                $('#timer').html('FINISHED');
            } else {
                t = Number(Math.round(t * 10) / 10).toFixed(1);
                $('#timer').html(t);
            }
        }
    }

    setInterval(show_countdown, 500);


Controlling reliability of the connection
-----------------------------------------

The important moment of the web interface chosen for automation systems is the
reliability of the connection.

Common problems which may arise:

* SFA server reboot and loss of session data.
* Breaking the WebSocket connection due to frontend reboot or another reason.

To control the session, SFA Framework requests SFA API :ref:`test<sfa_test>`
every **eva_sfa_heartbeat_interval** (*5* seconds by default). WebSocket is
additionally controlled by the framework using { 's': 'ping' } packet, whereto
the server should send a response { 's': 'pong' }. If there is no response
within the time exceeding heartbeat interval, the connection is considered
broken.

In case of the short-term problems with the server, it will be enough to set
the default value

.. code-block:: javascript

    eva_sfa_heartbeat_error = eva_sfa_restart;

and keep login/password in **eva_sfa_login** and **eva_sfa_password
variables**, or API key in **eva_sfa_apikey**. If an error occurs,
heartbeat will attempt to restart the framework once. If it fails or the
variable data has been deleted after the initial authorization, the function
specified in **eva_sfa_cb_login_error** will be called.

If your interface cleans up the authorization data, **eva_sfa_heartbeat_error**
should do the following:

.. code-block:: javascript

    eva_sfa_heartbeat_error = function() {
        // stop framework, make another attempt to log out
        // if the login/password were used
       eva_sfa_stop(
            // your function that displays the authorization form
            show_login_form 
            );
        }

In case reconnection is automatic, heartbeat error calls **eva_sfa_restart()**
that, in turn, calls **eva_sfa_cb_login_error** in case of failure.

And for automatic reconnection it should look like:

.. code-block:: javascript

    eva_sfa_cb_login_error = function(data) {
        if (data.status == 403) {
            // if the server returned error 403 (authentication failed
            // due to invalid auth data), the user should get a login form
            show_login_form();
            } else {
            // in case of another errors - try to restart framework in 3 seconds
            // and attempt to connect again
            setTimeout(eva_sfa_start, 3 * 1000);
            }
       }

