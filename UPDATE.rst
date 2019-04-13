EVA ICS 3.2.1
*************

What's new
==========

This version is a minor, but important update, which brings stability
improvements and removes obsolete functionality.

New features:

* AWS and Azure IoT support
* Modbus slave monitoring functions

Complete change log: https://get.eva-ics.com/3.2.1/stable/CHANGELOG.html

Update instructions
===================

Before update
-------------

.. warning::

    To avoid updating problems, apply this update only to version 3.2.0

Before applying this update

* test your key items and macros/scripts in a test sandbox
* make full backup of EVA ICS folder

Starting form version 3.2.1, EVA ICS is run with Python 3 venv. Make sure
Python 3 virtual environment module (*python3-virtualenv*) is installed.

If heavy python modules (e.g. *pandas*) were installed by OS package manager,
before applying an update, create file *./etc/venv* with the following context:

    # build virtualenv with system pip3 (should be installed)
    #USE_SYSTEM_PIP=1
    # use system packages if available
    SYSTEM_SITE_PACKAGES=1
    # skip packages, space separated
    SKIP="pandas"
    #PIP_EXTRA_OPTIONS=-v

Also, version 3.2.1 no longer requires obsolete retain MQTT topics except item
"shadow" state. However *status* and *value* subtopics can still be used to
update item states via MQTT. To avoid any possible conflicts:

* manually stop all nodes in cluster (*eva server stop*)
* clean up MQTT database or remove retain MQTT topics
* start update process on each node (*eva update*)

After update
------------

