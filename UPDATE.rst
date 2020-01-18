EVA ICS 3.3.0
*************

What's new
==========

- New core, faster inter-connect protocols
- UPnP controller discovery in local networks
  Core scripts engine

Complete change log: https://get.eva-ics.com/3.3.0/stable/CHANGELOG.html

Update instructions
===================

WARNING: Python 3.6+ is required.

EVA ICS 3.3.0 can handle API calls via MQTT from the previous versions, but not
vice-versa.

It's recommended to update controllers in order:

* nodes with UC instances
* nodes with LM PLC instances
* nodes with SFA instances

