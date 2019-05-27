SFA Framework
*************

SFA Framework is a component of :doc:`/sfa/sfa` that allows you to quickly
create a web application with EVA interface for a specific configuration.

**ui** folder contains *js/eva_sfa.js* file, the framework itself and
**lib/jquery*.js** - `jQuery <https://jquery.com/>`_, necessary for correct
operation. Lib folder also contains `Bootstrap <http://getbootstrap.com/>`_
files often used for web application development.

.. note::

    SFA Framework requires :doc:`API session tokens</api_tokens>` (enabled by
    default)

.. contents::

Framework connection
====================

Open the file *ui/index.html* in the editor, connect jQuery and SFA Framework:

.. code-block:: html

    <script src="lib/jquery.min.js"></script>
    <script src="js/eva_sfa.min.js"></script>

To use chart functions, additionally:

.. code-block:: html

    <script src="lib/moment.min.js"></script>
    <script src="lib/chart.min.js"></script>

To generate QR codes:

.. code-block:: html

    <script src="lib/qrious.min.js"></script>

Callback functions and handlers
===============================

* **success functions** are called with one parameter containing API call
  result dict

* **error functions** are called with 3 parameters:

    * **code** API call error code
    * **msg** API call error message
    * **response** full API response dict (if available)


.. _sfw_cat_general:

General functions and variables
===============================


.. _sfw_eva_sfa_framework_version:

eva_sfa_framework_version
-------------------------

Framework version

.. code-block:: javascript

    eva_sfa_framework_version = '3.2.3';


.. _sfw_eva_sfa_server_info:

eva_sfa_server_info
-------------------

After successfull login contains server info (API test function output). Data is refreshed every eva_sfa_heartbeat_interval seconds

.. code-block:: javascript

    eva_sfa_server_info = null;


.. _sfw_eva_sfa_framework_build:

eva_sfa_framework_build
-----------------------

Framework build

.. code-block:: javascript

    eva_sfa_framework_build = 2019052502;


.. _sfw_eva_sfa_tsdiff:

eva_sfa_tsdiff
--------------

Contains difference (in seconds) between server and client time

.. code-block:: javascript

    eva_sfa_tsdiff = null;


.. _sfw_eva_sfa_heartbeat_interval:

eva_sfa_heartbeat_interval
--------------------------

Heartbeat interval. Requests to API function "test" (system info), in seconds

.. code-block:: javascript

    eva_sfa_heartbeat_interval = 5;


.. _sfw_eva_sfa_ajax_reload_interval:

eva_sfa_ajax_reload_interval
----------------------------

Reload interval for AJAX mode (in seconds)

.. code-block:: javascript

    eva_sfa_ajax_reload_interval = 2;


.. _sfw_eva_sfa_cb_states_loaded:

eva_sfa_cb_states_loaded
------------------------

State callback. Contains function called after framework loads initial item states

.. code-block:: javascript

    eva_sfa_cb_states_loaded = null;


.. _sfw_eva_sfa_force_reload_interval:

eva_sfa_force_reload_interval
-----------------------------

Reload interval for WS mode (in seconds), to get data in case something is wrong with WS

.. code-block:: javascript

    eva_sfa_force_reload_interval = 5;


.. _sfw_eva_sfa_heartbeat_error:

eva_sfa_heartbeat_error
-----------------------

Heartbeat error handler. Contains function called if heartbeat got an error (usually user is forcibly logged out). The function is called as f(code, msg, data) if there's HTTP error data or f() if there's no HTTP error data (e.g.  unable to send WebSocket message)

.. code-block:: javascript

    eva_sfa_heartbeat_error = eva_sfa_restart;


.. _sfw_eva_sfa_reload_handler:

eva_sfa_reload_handler
----------------------

Reload events handler (WebSocket mode only). Contains function which's called as f() when reload event is received (server ask the clients to reload the interface)

.. code-block:: javascript

    eva_sfa_reload_handler = null;


.. _sfw_eva_sfa_server_restart_handler:

eva_sfa_server_restart_handler
------------------------------

Server restart handler (WebSocket mode only). Contains function which's called as f() when server restart event is received (server warns the clients about it's restart)

.. code-block:: javascript

    eva_sfa_server_restart_handler = null;


.. _sfw_eva_sfa_state_updates:

eva_sfa_state_updates
---------------------

Update item states via AJAX and subscribe to state updates via WebSocket
 
Possible values:  true - get states of all items API key has access to  {'p': [types], 'g': [groups]} - subscribe to specified types and groups  false - disable state updates

.. code-block:: javascript

    eva_sfa_state_updates = true;


.. _sfw_eva_sfa_ws_event_handler:

eva_sfa_ws_event_handler
------------------------

WebSocket event handler. Contains function which's called as f(data) when ws event is received function should return true, if it return false, WS data processing is stopped

.. code-block:: javascript

    eva_sfa_ws_event_handler = null;


.. _sfw_eva_sfa_ws_mode:

eva_sfa_ws_mode
---------------

WebSocket mode if true, is set by eva_sfa_init(). Setting this to false will force AJAX mode

.. code-block:: javascript

    eva_sfa_ws_mode = true;




.. _sfw_eva_sfa_call:

eva_sfa_call - call API function
--------------------------------

Calls any available SFA API function

.. code-block:: javascript

    function eva_sfa_call(func, params, cb_success, cb_error)

Parameters:

* **func** API function
* **params** function params
* **cb_success** function called on success
* **cb_error** function called if error occured

.. _sfw_eva_sfa_init:

eva_sfa_init - initialize Framework
-----------------------------------

Initializes eva_sfa javascript API automatically sets WebSocket or AJAX mode depending on the browser features.
The function is called automatically after script is loaded or can be re-called manually later

.. code-block:: javascript

    function eva_sfa_init()

.. _sfw_eva_sfa_restart:

eva_sfa_restart - restart Framework API
---------------------------------------

e.g. used on heartbeat error

.. code-block:: javascript

    function eva_sfa_restart()


.. _sfw_cat_auth:

Authentication
==============


.. _sfw_eva_sfa_login:

eva_sfa_login
-------------

Should always contain authentication login or API will be unable to reconnect in case of e.g. server reboot

.. code-block:: javascript

    eva_sfa_login = '';


.. _sfw_eva_sfa_password:

eva_sfa_password
----------------

Should always contain authentication password

.. code-block:: javascript

    eva_sfa_password = '';


.. _sfw_eva_sfa_apikey:

eva_sfa_apikey
--------------

Use API key instead of login. Insecure but fine for testing and specific configs

.. code-block:: javascript

    eva_sfa_apikey = null;


.. _sfw_eva_sfa_set_auth_cookies:

eva_sfa_set_auth_cookies
------------------------

Use auth cookies for /ui, /pvt and /rpvt

.. code-block:: javascript

    eva_sfa_set_auth_cookies = true;


.. _sfw_eva_sfa_cb_login_success:

eva_sfa_cb_login_success
------------------------

Successful login callback. Contains function called after successful login

.. code-block:: javascript

    eva_sfa_cb_login_success = null;


.. _sfw_eva_sfa_cb_login_error:

eva_sfa_cb_login_error
----------------------

Failed login callback. Contains function called after failed login

.. code-block:: javascript

    eva_sfa_cb_login_error = null;


.. _sfw_eva_sfa_api_token:

eva_sfa_api_token
-----------------

Contains current API token after log in. Filled by framework automatically

.. code-block:: javascript

    eva_sfa_api_token = '';


.. _sfw_eva_sfa_authorized_user:

eva_sfa_authorized_user
-----------------------

Contains authorized user name. Filled by framework automatically

.. code-block:: javascript

    eva_sfa_authorized_user = null;


.. _sfw_eva_sfa_logged_in:

eva_sfa_logged_in
-----------------

True if framework engine is started and user is logged in, false if not. Should not be changed outside framework functions

.. code-block:: javascript

    eva_sfa_logged_in = false;




.. _sfw_eva_sfa_erase_token_cookie:

eva_sfa_erase_token_cookie - erase auth token cookie
----------------------------------------------------

It's recommended to call this function when login form is displayed to prevent old token caching

.. code-block:: javascript

    function eva_sfa_erase_token_cookie()

.. _sfw_eva_sfa_start:

eva_sfa_start - start Framework API
-----------------------------------

After calling the function will authenticate user, open WebSocket (in case of WS mode) or schedule AJAX refresh interval.

.. code-block:: javascript

    function eva_sfa_start()

.. _sfw_eva_sfa_stop:

eva_sfa_stop - stop Framework API
---------------------------------

After calling the function will close open WebSocket if available, clear all the refresh intervals then try to close server session

.. code-block:: javascript

    function eva_sfa_stop(cb)


.. _sfw_cat_events:

Item events
===========




.. _sfw_eva_sfa_groups:

eva_sfa_groups - get groups list
--------------------------------



.. code-block:: javascript

    function eva_sfa_groups(params, cb_success, cb_error)

Parameters:

* **params** object with props

    * **p** item type (U for unit, S for sensor, LV for lvar)

    * **g** group filter (mqtt style)
* **cb_success** function called on success
* **cb_error** function called if error occured

.. _sfw_eva_sfa_register_update_state:

eva_sfa_register_update_state - register state update callback
--------------------------------------------------------------

Register the function to be called in case of state change event (or at first state load).
If state is already loaded, function will be called immediately

.. code-block:: javascript

    function eva_sfa_register_update_state(oid, cb)

Parameters:

* **oid** item id in format type:full_id, e.g. sensor:env/temp1
* **cb** function to be called

.. _sfw_eva_sfa_state:

eva_sfa_state - get item state
------------------------------



.. code-block:: javascript

    function eva_sfa_state(oid)

Parameters:

* **oid** item id in format type:full_id, e.g. sensor:env/temp1

Returns:

object state or undefined if no object found

.. _sfw_eva_sfa_state_history:

eva_sfa_state_history - get item state history
----------------------------------------------

@oid - item oid, list or comma separated

.. code-block:: javascript

    function eva_sfa_state_history(oid, params, cb_success, cb_error)

Parameters:

* **params** state history params
* **cb_success** function called on success
* **cb_error** function called if error occured

.. _sfw_eva_sfa_status:

eva_sfa_status - get item status
--------------------------------



.. code-block:: javascript

    function eva_sfa_status(oid)

Parameters:

* **oid** item id in format type:full_id, e.g. sensor:env/temp1

Returns:

object status(int) or undefined if no object found

.. _sfw_eva_sfa_value:

eva_sfa_value - get item value
------------------------------



.. code-block:: javascript

    function eva_sfa_value(oid)

Parameters:

* **oid** item id in format type:full_id, e.g. sensor:env/temp1

Returns:

object value (null, string or numeric if possible) or undefined if no object found


.. _sfw_cat_mgmt:

Macro execution and unit management
===================================




.. _sfw_eva_sfa_action:

eva_sfa_action - execute unit action
------------------------------------



.. code-block:: javascript

    function eva_sfa_action(unit_id, params, cb_success, cb_error)

Parameters:

* **unit_id** full unit ID
* **params** object with props

    * **s** new unit status (int)

    * **v** new unit value (optional)

    * **w** seconds to wait until complete

    * **p** action priority (optional)

    * **u** action uuid (optional)
* **cb_success** function called on success
* **cb_error** function called if error occured

.. _sfw_eva_sfa_action_toggle:

eva_sfa_action_toggle - execute unit toggle action
--------------------------------------------------



.. code-block:: javascript

    function eva_sfa_action_toggle(unit_id, params, cb_success, cb_error)

Parameters:

* **unit_id** full unit ID
* **params** object with props

    * **v** new unit value (optional)

    * **w** seconds to wait until complete

    * **p** action priority (optional)

    * **u** action uuid (optional)
* **cb_success** function called on success
* **cb_error** function called if error occured

.. _sfw_eva_sfa_kill:

eva_sfa_kill - kill running unit action and clean queue
-------------------------------------------------------



.. code-block:: javascript

    function eva_sfa_kill(unit_id, cb_success, cb_error)

Parameters:

* **unit_id** full unit ID

.. _sfw_eva_sfa_q_clean:

eva_sfa_q_clean - clean queue for unit
--------------------------------------



.. code-block:: javascript

    function eva_sfa_q_clean(unit_id, cb_success, cb_error)

Parameters:

* **unit_id** full unit ID

.. _sfw_eva_sfa_result:

eva_sfa_result - get action result
----------------------------------



.. code-block:: javascript

    function eva_sfa_result(params, cb_success, cb_error)

Parameters:

* **params** object with props

    * **i** object oid (type:group/id), unit or lmacro

    * **u** action uuid (either i or u must be specified)

    * **g** filter by group

    * **s** filter by status (Q, R, F - queued, running, finished)
* **cb_success** function called on success
* **cb_error** function called if error occured

.. _sfw_eva_sfa_run:

eva_sfa_run - run macro
-----------------------



.. code-block:: javascript

    function eva_sfa_run(macro_id, params, cb_success, cb_error)

Parameters:

* **macro_id** full macro ID
* **params** object with props

    * **a** macro args

    * **kw** macro kwargs

    * **w** seconds to wait until complete

    * **p** action priority

    * **u** action uuid
* **cb_success** function called on success
* **cb_error** function called if error occured

.. _sfw_eva_sfa_terminate:

eva_sfa_terminate - terminate current unit action
-------------------------------------------------



.. code-block:: javascript

    function eva_sfa_terminate(unit_id, cb_success, cb_error)

Parameters:

* **unit_id** full unit ID

.. _sfw_eva_sfa_terminate_by_uuid:

eva_sfa_terminate_by_uuid - terminate current unit action by uuid
-----------------------------------------------------------------



.. code-block:: javascript

    function eva_sfa_terminate_by_uuid(uuid, cb_success, cb_error)

Parameters:

* **uuid** action uuid


.. _sfw_cat_lvar:

LVar management
===============




.. _sfw_eva_sfa_clear:

eva_sfa_clear - clear lvar
--------------------------

For timer - set status to 0, otherwise value to 0

.. code-block:: javascript

    function eva_sfa_clear(lvar_id, cb_success, cb_error)

Parameters:

* **lvar_id** full lvar ID

.. _sfw_eva_sfa_expires_in:

eva_sfa_expires_in - get lvar expiration time left
--------------------------------------------------



.. code-block:: javascript

    function eva_sfa_expires_in(lvar_id)

Parameters:

* **lvar_id** item id in format type:full_id, e.g. lvar:timers/timer1

Returns:

- seconds to expiration, -1 if expired, -2 if stopped

.. _sfw_eva_sfa_reset:

eva_sfa_reset - reset lvar
--------------------------

Set status/value to 1

.. code-block:: javascript

    function eva_sfa_reset(lvar_id, cb_success, cb_error)

Parameters:

* **lvar_id** full lvar ID

.. _sfw_eva_sfa_set:

eva_sfa_set - set lvar value
----------------------------



.. code-block:: javascript

    function eva_sfa_set(lvar_id, value, cb_success, cb_error)

Parameters:

* **lvar_id** full lvar ID
* **value** new lvar value, optional

.. _sfw_eva_sfa_toggle:

eva_sfa_toggle - toggle lvar value
----------------------------------

Toggle current value (if value is 0 or 1) useful when lvar is being used as flag

.. code-block:: javascript

    function eva_sfa_toggle(lvar_id, cb_success, cb_error)

Parameters:

* **lvar_id** full lvar ID


.. _sfw_cat_log:

Processing logs
===============
For log processing the client API key should have sysfunc=yes permission.

.. _sfw_eva_sfa_log_postprocess:

eva_sfa_log_postprocess
-----------------------

Log post processing callback function e.g. to autoscroll the log viewer

.. code-block:: javascript

    eva_sfa_log_postprocess = null;


.. _sfw_eva_sfa_log_records_max:

eva_sfa_log_records_max
-----------------------

Max log records to get/keep

.. code-block:: javascript

    eva_sfa_log_records_max = 200;


.. _sfw_eva_sfa_log_reload_interval:

eva_sfa_log_reload_interval
---------------------------

Log refresh interval for AJAX mode (in seconds)

.. code-block:: javascript

    eva_sfa_log_reload_interval = 2;


.. _sfw_eva_sfa_process_log_record:

eva_sfa_process_log_record
--------------------------

New log record handler

.. code-block:: javascript

    eva_sfa_process_log_record = null;




.. _sfw_eva_sfa_change_log_level:

eva_sfa_change_log_level - change log processing level
------------------------------------------------------



.. code-block:: javascript

    function eva_sfa_change_log_level(log_level)

Parameters:

* **log_level** log processing level

.. _sfw_eva_sfa_log_level_name:

eva_sfa_log_level_name - get log level name
-------------------------------------------



.. code-block:: javascript

    function eva_sfa_log_level_name(log_level)

Parameters:

* **log_level** log level id

.. _sfw_eva_sfa_log_start:

eva_sfa_log_start - start log processing
----------------------------------------



.. code-block:: javascript

    function eva_sfa_log_start(log_level)

Parameters:

* **log_level** log processing level (optional)


.. _sfw_cat_tools:

Utility functions
=================




.. _sfw_eva_sfa_chart:

eva_sfa_chart - display a chart
-------------------------------

To work with charts you should include Chart.js library, which is located in file lib/chart.min.js (ui folder).

.. code-block:: javascript

    function eva_sfa_chart(ctx, cfg, oid, params, _do_update)

Parameters:

* **ctx** html container element id to draw in (must have fixed width/height)
* **cfg** Chart.js configuration
* **oid** item oid or oids, array or comma separated (type:full_id)
* **params** object with props

    * **timeframe** timeframe to display (5T - 5 min, 2H - 2 hr, 2D - 2 days etc.), default: 1D

    * **fill** precision[:np] (10T - 60T recommended, more accurate - more data), np - number precision, optional. default: 30T:2

    * **update** update interval in seconds. If the chart conteiner is no longer visible, chart stops updating.

    * **prop** item property to use (default is value)

.. _sfw_eva_sfa_hi_qr:

eva_sfa_hi_qr - QR code for EvaHI
---------------------------------

Generates QR code for :doc:`EvaHI</evahi>`-compatible apps (e.g. for EVA ICS Control Center mobile app for Android). Current framework session must be authorized using user login. If eva_sfa_password is defined, QR code also contains password value. Requires qrious js library.

.. code-block:: javascript

    function eva_sfa_hi_qr(ctx, params)

Parameters:

* **ctx** html <canvas /> element id to generate QR code in
* **params** object with additional parameters:

    * **size** QR code size in px (default: 200)

    * **url** override UI url (default: document.location)

    * **user** override user (default: eva_sfa_authorized_user)

    * **password** override password

Returns:

true if QR code is generated

.. _sfw_eva_sfa_load_animation:

eva_sfa_load_animation - animate html element block
---------------------------------------------------

Simple loading animation

.. code-block:: javascript

    function eva_sfa_load_animation(el_id)

Parameters:

* **el_id** html element id

.. _sfw_eva_sfa_popup:

eva_sfa_popup - popup window
----------------------------

Opens popup window. Requires bootstrap css included There may be only 1 popup opened. If the page want to open another popup, the current one will be overwritten unless it's class is higher than a new one.

.. code-block:: javascript

    function eva_sfa_popup(ctx, pclass, title, msg, params)

Parameters:

* **ctx** html element id to use as popup (any empty <div /> is fine)
* **pclass** popup class: info, warning or error. opens big popup window if '!' is put before the class (e.g. !info)
* **title** popup window title
* **msg** popup window message
* **params** object with handlers and additional parameters:

    * **ct** popup auto close time (sec), equal to pressing escape

    * **btn1** button 1 name ('OK' if not specified)

    * **btn2** button 2 name

    * **btn1a** function to run if button 1 (or enter) is pressed

    * **btn2a** function(arg) to run if button 2 (or escape) is pressed. arg is true if the button was pressed, false if escape key or auto close.

    * **va** validate function which runs before btn1a. if the function return true, the popup is closed and btn1a function is executed. otherwise the popup is kept and the function btn1a is not executed. va function is used to validate an input, if popup contains any input fields.



Examples
========

Examples of the SFA framework usage are also provided in
":doc:`/tutorial/tut_ui`" part of the EVA :doc:`tutorial</tutorial/tutorial>`.

.. _sfw_example_general:

Framework start
---------------

.. code-block:: javascript

    /**
    * Hide login form and show primary interface <div />
    */
    function after_login() {
        $('#login_form').hide();
        $('#interface').show();
    }

    /**
    * Show error message
    */
    function failed_login(code, msg, response) {
        $('#login_form_error').html(msg);
    }

    $(document).ready(function() {
        eva_sfa_cb_login_success = after_login;
        eva_sfa_cb_login_error = failed_login;
        // as this is primary page, erase token cookie if set
        eva_sfa_erase_token_cookie();
        // function ui_set_sensor will handle sensor event by the specified mask
        eva_sfa_register_update_state('sensor:greenhouse*/env/temp', ui_set_sensor);
        eva_sfa_register_update_state('sensor:greenhouse*/env/hum', ui_set_sensor);
        // function for login form submit event
        $('#login_form').submit(function(e) {
          e.preventDefault();
          eva_sfa_login = e.currentTarget.login.value;
          eva_sfa_password = e.currentTarget.password.value;
          eva_sfa_start();
          });
    }


.. _sfw_example_timer:

Timer example
-------------

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

.. _sfw_chart_example:

Chart example
-------------

We have 2 sensors, for internal and external air temperature and want their
data to be placed in one chart.

Chart options:

.. code-block:: javascript

    var chart_opts = {
            responsive: false,
            //animation: false,
            legend: {
                display: true
            },
            scales: {
                xAxes: [{
                    type: "time",
                    time: {
                        unit: 'hour',
                        unitStepSize: 1,
                        round: 'minute',
                        tooltipFormat: "H:mm:ss",
                        displayFormats: {
                          hour: 'MMM D, H:mm'
                        }
                    },
                    ticks: {
                        minRotation: 90,
                        maxTicksLimit: 12,
                        autoSkip: true
                    },
                    display: true,
                }],
                yAxes: [{
                    display: true,
                    ticks: {
                    },
                    scaleLabel: {
                        display: true,
                        labelString: 'Degrees'
                    }
                }]
            }
        }

Chart configuration:

.. code-block:: javascript

    var chart_cfg = {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                label: 'Temperature inside',
                data: [],
                fill: false,
                backgroundColor: 'red',
                borderColor: 'red'
                },
                {
                label: 'Temperature outside',
                data: [],
                fill: false,
                backgroundColor: 'blue',
                borderColor: 'blue'
                }
            ],
        },
        options: chart_opts
    }

Chart code (consider *<div id="chart1" style="display: none"></div>* is placed
somewhere in HTML), data for last 8 hours, 15 min precision, update every 10
seconds:

.. code-block:: javascript

    eva_sfa_chart(
        'chart1',
        chart_cfg,
        'sensor:env/temp_inside,sensor:env/temp_outside',
        {timeframe: '8H', fill:'15T', update:10});

.. _sfw_example_log:

Log viewer example
------------------

The following example shows how to build a log viewer, similar to included in
:doc:`/uc/uc_ei` and :doc:`/lm/lm_ei`.

.. code-block:: html

  <html>
    <head>
    <script src="lib/jquery.min.js"></script>
    <script src="js/eva_sfa.js"></script>
    <style type="text/css">
      #logr {
        outline: none;
        width: 100%;
        height: 60% !important;
        font-size: 11px;
        overflow: scroll;
        overflow-x: hidden;
        margin-bottom: 10px;
        border-style : solid;
        border-color : #3ab0ea;
        border-color : rgba(58, 176, 234, 1);
        border-width : 2px;
        border-radius : 5px;
        -moz-border-radius : 5px;
        -webkit-border-radius : 5px;
        }
      .logentry.logentry_color_10 { color: grey }
      .logentry.logentry_color_20 { color: black }
      .logentry.logentry_color_30 {
        color: orange;
        font-weight: bold;
        font-size: 14px
        }
      .logentry.logentry_color_40 {
        color: red;
        font-weight: bold;
        font-size: 16px
      }
      .logentry.logentry_color_50 {
        color: red;
        font-weight: bold;
        font-size: 20px;
        animation: blinker 0.5s linear infinite;
      }
      @keyframes blinker {  
        50% { opacity: 0; }
      }
    </style>
    </head>
    <body>
    <div id="logr"></div>
    <script type="text/javascript">
        function time_converter(UNIX_timestamp) {
          var a = new Date(UNIX_timestamp * 1000);
          var year = a.getFullYear();
          var month = a.getMonth() + 1;
          var date = a.getDate();
          var hour = a.getHours();
          var min = a.getMinutes();
          var sec = a.getSeconds();
          var time =
            year +
            '-' +
            pad(month, 2) +
            '-' +
            pad(date, 2) +
            ' ' +
            pad(hour, 2) +
            ':' +
            pad(min, 2) +
            ':' +
            pad(sec, 2);
          return time;
        }

        function pad(num, size) {
          var s = num + '';
          while (s.length < size) s = '0' + s;
          return s;
        }

        function format_log_record(l) {
          return (
            '<div class="logentry logentry_color_' +
            l.l +
            '">' +
            time_converter(l.t) +
            ' ' +
            l.h +
            ' ' +
            l.p +
            ' ' +
            eva_sfa_log_level_name(l.l) +
            ' ' +
            l.mod +
            ' ' +
            l.th +
            ': ' +
            l.msg +
            '</div>'
          );
        }
        eva_sfa_process_log_record = function(l) {
          $('#logr').append(format_log_record(l));
          while ($('.logentry').length > eva_sfa_log_records_max) {
          $('#logr')
            .find('.logentry')
            .first()
            .remove();
          }
        }
        eva_sfa_log_postprocess = function() {
          $('#logr').scrollTop($('#logr').prop('scrollHeight'));
        }

        eva_sfa_apikey="SECRET_KEY_JUST_FOR_EXAMPLE_DONT_STORE_KEYS_IN_JS";
        eva_sfa_cb_login_success = function(data) {
            eva_sfa_log_records_max = 100;
            eva_sfa_log_start();
        }
        eva_sfa_start();
    </script>
    </body>
    </html>

Updating multiple values
------------------------

The following example will show how to update displayed values of 3 sensors
with one function. Define HTML elements:

.. code-block:: html

    <div>Sensor 1 value: <span id="sensor:group1/sensor1"></span></div>
    <div>Sensor 2 value: <span id="sensor:group1/sensor2"></span></div>
    <div>Sensor 3 value: <span id="sensor:group1/sensor3"></span></div>

Then register update event function:

.. code-block:: javascript


    eva_sfa_register_update_state('sensor:group1/*', function(state) {
        $('#' + $.escapeSelector(state.oid)).html('S: ' + state.value);
    }

Multi-page interfaces
=====================

By default, the interface should be programmed in a single HTML/J2 document
*ui/index.html* or *ui/index.j2*, however sometimes it's useful to split parts
of the interface to different html page files.

Each HTML document should initialize/login SFA framework to access its
functions. However if *eva_sfa_set_auth_cookies* is set to *true*, the
secondary page can log in user with the existing token:

.. code-block:: javascript

    eva_sfa_cb_login_error = function() {
        // token is invalid or expired, redirect user to main page
        document.location = '/ui/';
    }
    eva_sfa_start();

If multi-page navigation includes navigation back to the main page, it should
perform a single authentication attempt to re-use existing token:

.. code-block:: javascript

    ui_first_auth = true;

    eva_sfa_cb_login_error = function(code, msg, data) {
        // show login form
        // ..........
        if (ui_first_auth) {
            ui_first_auth = false;
        } else {
            // display login error
            // e.g.
            // $('login_error_msg').html(msg);
        }
    }
    eva_sfa_start();

Controlling reliability of the connection
=========================================

An important moment of the web interface chosen for automation systems is
reliability of the connection.

Common problems which may arise:

* SFA server reboot and loss of session data.
* Breaking the WebSocket connection due to front-end reboot or another reason.

To control the session, SFA Framework requests SFA API :ref:`test<sfapi_test>`
every **eva_sfa_heartbeat_interval** (*5* seconds by default). WebSocket is
additionally controlled by the framework using { 's': 'ping' } packet, whereto
the server should send a response { 's': 'pong' }. If there is no response
within the time exceeding heartbeat interval, the connection is considered
broken.

In case of short-term problems with the server, it will be enough to set the
default value

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
            // in case of other errors - try to restart framework in 3 seconds
            // and attempt to connect again
            setTimeout(eva_sfa_start, 3 * 1000);
            }
       }


Authentication with front-end server
====================================

If you have front-end server installed before UI and it handles HTTP basic
authentication, you can leave **eva_sfa_login** and **eva_sfa_apikey**
variables empty and let framework log in without them.

In this case authorization data will be parsed by SFA server from Authorization
HTTP header (front-end server should pass it as-is to back-end SFA).