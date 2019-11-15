EVA ICS 3.2.6
*************

What's new
==========

- Msgpack support

Complete change log: https://get.eva-ics.com/3.2.6/stable/CHANGELOG.html

Update instructions
===================

EVA ICS 3.2.6 can handle API calls via MQTT from the previous versions, but not
vice-versa.

If controllers are inter-connected via MQTT, update them in order:

* nodes with UC instances
* noes with LM PLC instances
* nodes with SFA instances
