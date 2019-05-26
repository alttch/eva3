Building an interface with SFA Framework
****************************************

* EVA Tutorial parts

  * :doc:`Intro<tutorial>`
  * :doc:`tut_uc`
  * :doc:`tut_lm`
  * :doc:`tut_sfa`
  * **Building an interface with SFA Framework** << we are here

So, let us proceed with our configuration. :doc:`/uc/uc`, :doc:`/lm/lm` and
:doc:`/sfa/sfa` have already been configured.

The last step is to create the user interface with :doc:`/sfa/sfa_framework`.

.. contents::

Configuring authentication keys
===============================

.. include:: skip_easy.rst

Create an SFA :ref:`API key<sfa_apikey>` named **operator** in
**etc/sfa_apikeys.ini**:

.. code-block:: ini

    [operator]
    key = opsecret
    groups = #
    pvt = #
    hosts_allow = 0.0.0.0/0

and restart :doc:`SFA</sfa/sfa>`:

.. code-block:: bash

    eva sfa server restart

Configuring users
=================

Create a login for the user to use with **operator** key:

.. code-block:: bash

    eva sfa user create john verysecret operator

Create a web application
========================

Use :doc:`/sfa/sfa_framework` to write a simple web application to manage our
example setup. Create a new **index.html** file and put it to **ui** folder:

If the :doc:`item</items>` ids or other information should be hidden from
unauthorized users, the additional .js files with such data may be served by
:doc:`/sfa/sfa_pvt` or frontend server with additional authentication.

.. code-block:: html

    <html>
     <head>
       <title>Plant1 interface</title>
       <script src="lib/jquery.min.js"></script>
       <script src="js/eva_sfa.min.js"></script>
     </head>
    <body>
    <!-- simple authentication form -->
     <div id="loginform">
        <form onsubmit="do_login(); return false">
        Login:
            <input type="text" size="10" name="login" id="i_login" value="" />
            <br />
        Password:
            <input type="password" size="10" name="password"
                id="i_password" value="" /><br />
             <input type="submit" name="submit" value="GO" />
        </form>
     </div>
     <!-- interface and controls -->
     <div id="interface" style="display: none">
      <div>Temperature: <span id="temp1"></span></div>
      <div>Internal ventilation:
        <a onclick="eva_sfa_action_toggle('ventilation/vi')" href="#">
            <span id="vi"></span></a>
      </div>
      <div>External ventilation:
        <a onclick="eva_sfa_action_toggle('ventilation/ve')" href="#">
            <span id="ve"></span></a>
      </div>
      <div>Hall light:
        <a onclick="eva_sfa_action_toggle('light/lamp1')" href="#">
            <span id="lamp1"></span></a>
      </div>
      <div>Alarm system:
        <a onclick="eva_sfa_toggle('security/alarm_enabled')" href="#">
            <span id="alarm_enabled"></span></a>
      </div>
      <div style="margin-top: 30px">
        <a onclick="eva_sfa_stop(show_login_form)" href="#">logout</a>
      </div>
     </div>
     <script type="text/javascript">
    
     var ed_labels = [ 'DISABLED', 'ENABLED' ];
    
     // function starting SFA Framework after the
     // authentication form has been submitted
     function do_login() {
       $('#loginform').hide();
       eva_sfa_login = $('#i_login').val();
       eva_sfa_password = $('#i_password').val();
       eva_sfa_start();
     }
    
     // function displaying the authentication form
     function show_login_form(data) {
       eva_sfa_password = '';
       $('#interface').hide();
       $('#i_login').val(eva_sfa_login);
       $('#i_password').val('');
       $('#loginform').show();
       }
    
     // after the page is loaded
     $(document).ready(function() {
       // initialize SFA Framework
       eva_sfa_init();
       // erase token cookie if cached
       eva_sfa_erase_token_cookie();
       // after the authentication succeeds the main interface is displayed
       eva_sfa_cb_login_success = function(data) { $('#interface').show(); }
       // if there is a login error
       eva_sfa_cb_login_error = function(code, msg, data) {
           // end session and display the authentication form,
           // if auth data is incorrect
           if (code == 2) { 
               show_login_form();
               } else {
               // otherwise - repeat the attempts every 2 seconds
               // until the server responds
               setTimeout(eva_sfa_start, 1 * 2000);
               }
           }
       // register the event handlers
       eva_sfa_register_update_state(
            'sensor:env/temp1', function(state) {$('#temp1').html(state.value)})
       eva_sfa_register_update_state(
            'unit:ventilation/vi',
            function(state) {$('#vi').html(ed_labels[state.status])});
       eva_sfa_register_update_state(
            'unit:ventilation/ve',
            function(state) {$('#ve').html(ed_labels[state.status])});
       eva_sfa_register_update_state(
            'unit:light/lamp1',
            function(state) {$('#lamp1').html(ed_labels[state.status])});
       eva_sfa_register_update_state(
            'lvar:security/alarm_enabled',
            function(state) {$('#alarm_enabled').html(ed_labels[state.value])});
     })
     </script>
    </body>
    </html>

Our setup is complete. Interface is available at the following address:

.. code-block:: bash

    http(s)://<IP_address_SFA:Port>/

The default port for SFA is 8828.
