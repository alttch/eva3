EVA ICS 3.3.0
*************

What's new
==========

- New core, faster inter-connect protocols
- UPnP controller discovery in local networks
- Core scripts engine

Complete change log: https://get.eva-ics.com/3.3.0/stable/CHANGELOG.html

Update instructions
===================

WARNING: Python 3.6+ is required. Upgrade system Python and rebuild EVA ICS
venv:

* cd /opt/eva
* rm -rf python3
* ./install/build-venv

If newer Python version installed not system-wide:

* Download *build-venv* from 3.3.0:
  https://raw.githubusercontent.com/alttch/eva3/3.3.0/install/build-venv
* Put it to /opt/eva/install/ directory
* chmod +x /opt/eva/install/build-venv
* put PYTHON=/path/to/python to /opt/eva/etc/venv
* Follow the first list of instructions and rebuild EVA ICS venv

EVA ICS 3.3.0 can handle API calls via MQTT from the previous versions, but not
vice-versa.

It's recommended to update controllers in order:

* nodes with UC instances
* nodes with LM PLC instances
* nodes with SFA instances

