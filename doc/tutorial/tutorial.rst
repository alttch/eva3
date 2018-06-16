Tutorial
========

In this section, we will focus on EVA configuration which is illustrated by the
following example.

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
* and some alarm system installed on the remote server and called by its own
  API (via GET request). As soon as alarm is activated, it switches on the
  alarm sirene and sends SMS to the operator.

Our task is to automate the above:

* To switch on the internal ventilation every night for the period from 9pm
  till 7am.

* To switch ventilation in the daytime, if the air temperature is above 25
  degrees for more than 5 minutes in a row.

* If the sensor detect a motion, do the following:

  * if the alarm is on - send API request to the alarm system
  * if the alarm is off - turn on the light in a hall

* The user should be able to control the ventilation system with web interface,
  see the temperature, manage alarm and lighting

Let's do this step by step, from the equipment configuration to interface
development. Suppose that EVA has already been :doc:`installed</install>` and
everything is located on the single server, including :ref:`MQTT<mqtt_>` server
with *eva:secret* access and all the data will be sent into *plant1* subject.

EVA **bin** folder is included in system **PATH**.

All operations will be done using :doc:`command line applications</cli>`.

* EVA Tutorial parts

  * :doc:`tut_uc`
  * :doc:`tut_lm`
  * :doc:`tut_sfa`
  * :doc:`tut_ui`
