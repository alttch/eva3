Quick start
***********

Installation
============

Get `any supported Linux distro <https://www.eva-ics.com/download>`_. And
install EVA ICS with the default settings:

.. code:: bash

    curl geteva.cc | sh /dev/stdin -a

This installs all EVA ICS components on a single machine and automatically
links them together.

Alternatively, `EVA ICS docker image
<https://hub.docker.com/r/altertech/eva-ics>`_ can be used.

Task
====

Let us have a temperature sensor and a fan, both controlled with modbus. We
want to:

* Monitor state of both and control the fan from UI

* Turn the fan on when the temperature reaches 25C.

* Turn the fan off when the temperature reaches 22C.

Connecting the equipment
========================

Equipment in EVA ICS is managed by :doc:`/uc/uc`.

.. note::

    It is much faster to use the interactive mode ("eva -I" or "eva-shell") but
    in this document commands are provided as they should be executed from the
    system shell.

Download Modbus PHI modules:

.. code:: shell

    eva uc phi download https://get.eva-ics.com/phi/modbus/modbus_xvunit.py
    eva uc phi download https://get.eva-ics.com/phi/modbus/modbus_sensor.py 

Define Modbus virtual port. Consider it is on /dev/ttyS0 (system RS-232 port
#1):

.. code:: shell

    eva uc modbus create local0 rtu:/dev/ttyS0:8600:8:N:1

.. note::

    If Docker image is used, either map ttyS0 device from the host or run the
    container in privileged mode.

Create the items

.. code:: shell

    eva uc create unit:room1/fan --enable
    eva uc create sensor:room1/temp --enable

Define drivers and assign them to the items. Consider the fan control relay is
on Modbus unit 0x01 and is controlled by coil #0 and the temperature sensor is
on Modbus unit 0x02 and its value is stored to holding registers h0-h1 as IEE
754a 32-bit float.

.. code:: shell

    eva uc phi load mctrl modbus_xvunit -c port=local0,unit=1
    eva uc phi load mmon modbus_sensor -c port=local0,unit=2

    # for modbus drivers, "port" means a register
    eva uc driver assign unit:room1/fan mctrl.default -c port=c0
    eva uc driver assign sensor:room1/temp mmon.default -c port=h0,_type=f32

    # let us update sensor every 5 seconds
    eva uc config set sensor:room1/temp update_interval 5

    # check the sensor value
    eva uc state -p sensor

    # turn on / off the fan manually, "-w 5" means wait 5 seconds for the
    # action finish

    eva uc action toggle unit:room1/fan -w 5

    # check fan (visually and unit status)
    eva uc state -p unit

Defining logic
==============

Logic in EVA ICS is managed by :doc:`/lm/lm`.

To automatically control the fan, a :doc:`macro </lm/macros>` may be created,
but in this simple example we will call actions directly from :doc:`decision
rules </lm/decision_matrix>`.

.. code:: shell

    eva lm rule create if sensor:room1/temp.value > 25 then @action(unit:room1/fan, status=1)
    eva lm rule create if sensor:room1/temp.value < 22 then @action(unit:room1/fan, status=0)

Putting "@" symbol tells the rule to call macro function "action" directly,
instead of compiling and executing a user-defined macro.

.. note::

    The newly crated UC items are synced with LM PLC automatically every 30
    seconds. To sync them manually, use "eva lm controller reload" command.

Building a very simple Human-Machine Interface
==============================================

Interfaces and combined API for 3rd-party applications in EVA ICS is provided
by :doc:`/sfa/sfa`.

Install `EVA JS Framework <https://github.com/alttch/eva-js-framework>`_:

.. code:: shell

    eva sfa server pkg-install -w 60 https://github.com/alttch/eva-js-framework/releases/download/v0.3.24/eva-js-framework-0.3.24.evapkg

By default, EVA ICS creates in SFA "operator" API key and "operator" user, but
let us create a new API key and use it directly:

.. code:: shell

    eva sfa key create op
    eva sfa key set op key 123

.. note::

    The newly crated UC and LM PLC items are synced with SFA automatically
    every 30 seconds. To sync them manually, use "eva lm controller reload"
    command.

Put the following HTML to "ui/index.html". Any Javascript framework can be
used, but in this example we will use pure vanilla JS only:

.. code:: html

    <html>
    <head>
        <title>My first cool EVA-ICS HMI</title>
    <script type="text/javascript" src="eva.framework.min.js"></script>
    </head>
    <body>
        <div>Temperature: <span id="temp"></span></div>
        <div>Fan:
            <input id="fan" type="button"
                onclick="$eva.call('action_toggle', 'unit:room1/fan')" /></div>
        <script type="text/javascript">
        $eva.apikey = "123";
        $eva.watch('unit:room1/fan', function(state) {
            document.getElementById('fan').value = state.status?'ON':'OFF';
            });
        $eva.watch('sensor:room1/temp', function(state) {
            document.getElementById('temp').innerHTML = state.value;
            });
        $eva.start();
        </script>
    </body>
    </html>

Go to http://localhost:8828 (or IP of your system) and HMI application is ready
to go.
