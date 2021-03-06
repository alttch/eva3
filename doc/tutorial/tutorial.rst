Tutorial
********

In this section, we will focus on EVA configuration which is illustrated by the
following example.

.. note::

   Examples for the particular equipment can be also found in
   :ref:`integrations <integrations>` section of EVA ICS documentation.

There is a room and some equipment:

* Internal ventilation system, powered via SR-201 controlled relay, port 1
* External ventilation system, powered  via SR-201 controlled relay, port 2
* Air temperature sensor `Dallas DS18S20
  <http://pdfserv.maximintegrated.com/en/ds/DS18S20.pdf>`_

* a motion sensor in the hall connected to `AKCP SensorProbe
  <http://www.akcp.com/products/sensorprobe-series/>`_ 
* a light in the hall connected to `Denkovi SmartDEN IP-16R
  <http://denkovi.com/smartden-lan-ethernet-16-relay-module-din-rail-box>`_,
  port 2
* and some alarm system installed on a remote server and called by its own
  API (via GET request). As soon as the alarm is activated, it switches on the
  alarm siren and sends an SMS to the operator.

Our task is to automate the above:

* To switch on the internal ventilation every night for the period from 9pm
  till 7am.

* To switch on ventilation in the daytime, if the air temperature is above 25
  degrees for more than 5 minutes in a row.

* If the sensor detects a motion, do the following:

  * if the alarm is on - send an API request to the alarm system
  * if the alarm is off - turn on the light in the hall

* The user should be able to control the ventilation system with web interface,
  see the temperature, manage alarm and lighting

Let's do this step by step, from equipment configuration to interface
development. Let's Suppose that EVA has already been :doc:`installed</install>`
and everything is located on a single server, including :ref:`MQTT<mqtt_>`
server with *eva:secret* access and all the data will be sent into *plant1*
subject.

EVA **bin** folder is included in system **PATH**.

All operations will be done using :doc:`command line applications</cli>`.

.. toctree::
    :maxdepth: 1

    tut_uc
    tut_lm
    tut_sfa
    tut_ui
