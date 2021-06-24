AKCP
****

`AKCP <https://www.akcp.com/>`_ sensors can be integrated into :doc:`/uc/uc`
with either :doc:`SNMP traps </snmp>` or corresponding `PHI modules
<https://www.eva-ics.com/phi>`_.

Both ways require sensors to be connected to AKCP SensorProbe or SecurityProbe
device, which acts as SNMP bridge.

Equipment supported
===================

* **AKCP_MD00** motion detector
* **AKCP_SK00** smoke detector
* **AKCP_THSXX** temperature/humidity sensor

Setup
=====

All AKCP sensors send SNMP traps on connect/failure, detector sensors also send
traps on event.

Both ways (using SNMP trap parser or PHIs), require SNMP trap handler to be
properly configured and set in AKCP SensorProbe/SecurityProbe as a trap handler
server (field *snmptrap* of :ref:`uc_config`).

Consider AKCP SensorProbe IP is 192.168.1.100, motion detector is installed on
port 1, smoke detector - on port 2, temperature/humidity sensor - on port 4.

.. code:: shell

   # motion detector
   eva uc phi download https://get.eva-ics.com/phi/sensors/alarm/akcp_md.py
   # PHI module is loaded for the particular SensorProbe/port
   eva uc phi load md1 akcp_md -c host=192.168.1.100,sp=1 -y
   # create motion sensor
   eva uc create sensor:security/motion1 -y
   # assign driver to sensor
   eva uc driver assign sensor:security/motion1 md1.default -y

   # smoke detector
   eva uc phi download https://get.eva-ics.com/phi/sensors/alarm/akcp_sk.py
   eva uc phi load sk1 akcp_sk -c host=192.168.1.100,sp=2 -y
   # create smoke sensor
   eva uc create sensor:security/smoke1 -y
   # assign driver to sensor
   eva uc driver assign sensor:security/smoke1 sk1.default -y

   # temperature/humidity sensor
   eva uc phi download https://get.eva-ics.com/phi/sensors/env/akcp_ths.py
   # PHI for AKCP_THSXX provides 2 virtual ports: t and h
   eva uc phi load ths1 akcp_ths -c host=192.168.1.100,sp=4,retries=3 -y
   # create temperature and humidity sensors
   eva uc create sensor:env/temp1 -y
   eva uc create sensor:env/hum1 -y
   # assign driver to sensors
   eva uc driver assign sensor:env/temp1 ths1.default -c port=t -y
   eva uc driver assign sensor:env/hum1 ths1.default -c port=h -y
   # setup sensors to update state every 30 seconds
   config set sensor:env/temp1 update_interval 30 -y
   config set sensor:env/hum1 update_interval 30 -y

Performance tuning
==================

If AKCP_THSXX PHI becomes slow, it's recommended to install **python3-netsnmp**
module, which is much faster than native SNMP implementation:

Put *python3-netsnmp* to *EXTRA* var in /opt/eva/etc/venv, then run

.. code:: shell

   /opt/eva/install/build-venv

You will also probably need *libsnmp-dev* system package. Check module setup
output for details.
