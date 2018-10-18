Command line interfaces
***********************

.. contents::

EVA command line apps
=====================

EVA apps are used to configure the system and call controller API functions
from the command line or by external scripts. All of the following apps are
located in **bin** folder.

EVA shell
---------

EVA shell (**eva-shell**) is a primary CLI tool. It allows you to manage local
system as well as calling other tools directly from CLI interactive command
line.

With EVA shell you can install updates, backup and restore configuration,
start and stop EVA components.

Universal Controller
--------------------

* **uc-cmd** manages :doc:`/uc/uc`
* **uc-notifier** configures UC :doc:`notification system</notifiers>`
* **uc-tpl** generate and validate :ref:`device templates<device>`

* **uc-api** direct requests to :doc:`UC API</uc/uc_api>`. Use **-y** instead
  of **full** and **save** params.

Logic Manager
-------------

* **lm-cmd** manages :doc:`/lm/lm`
* **lm-rules** separate app for the :doc:`decision rules</lm/decision_matrix>`
  management
* **lm-notifier** configures LM PLC :doc:`notification system</notifiers>`

* **lm-api** direct requests to :doc:`LM API</lm/lm_api>`. Use **-y** instead
  of **full** and **save** params.

SCADA Final Aggregator
----------------------

* **sfa-cmd** manages :doc:`/sfa/sfa`
* **sfa-notifier** configures SFA :doc:`notification system</notifiers>`

* **sfa-api** direct requests to :doc:`SFA API</sfa/sfa_api>`. Use **-y**
  instead of **full** and **save** params.

Other
-----

* **test-uc-xc** a special app to test UC :doc:`item scripts</item_scripts>`.
  Launches an item script with UC :ref:`cvars<uc_cvars>` and EVA paths set in
  the environment.

* **sbin/layout-converter** allows to convert **simple** :ref:`item
  layout<item_layout>` to **enterprise**.

:doc:`Virtual item</virtual>` management is performed using **xc/evirtual**
application.

Legacy
------

In case of significant changes in the commands or arguments, previous versions
of command line tools are kept and moved to **legacy** folder. We strongly
recommend using API calls only in all 3rd-party applications, but if your app
uses command line interface, you can get the previous version until the app is
reprogrammed to use a new one.

Device control apps
===================

EVA distribution includes preinstalled samples for device controlling. All
sample scripts are located in **xbin** folder

TCP/IP controlled relays
------------------------

* **EG-PM2-LAN** controls `EG-PM2-LAN Smart PSU
  <http://energenie.com/item.aspx?id=7557>`_
* **SR-201** controls the SR-201 relay controllers - a quite popular and simple
  solution with TCP/IP management option

1-Wire
------

* **w1_ds2408** controls `Dallas
  DS2408 <https://datasheets.maximintegrated.com/en/ds/DS2408.pdf>`_-based
  relays on the local 1-Wire bus
* **w1_therm** monitors `Dallas DS18S20 <https://datasheets.maximintegrated.com/en/ds/DS18S20.pdf>`_, DS18B20 and other compatible temperature sensors on the local 1-Wire bus
* **w1_ls** displays the devices connected to the local 1-Wire bus
