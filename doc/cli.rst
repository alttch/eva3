Command line interfaces
=======================

.. contents::

EVA command line apps
---------------------

EVA apps are used to configure the system and call controller API functions
from the command line or by external scripts. All the following apps are locate
in **bin** folder.

Universal Controller
~~~~~~~~~~~~~~~~~~~~

* **uc-cmd** manages :doc:`/uc/uc`
* **uc-notifier** configures UC :doc:`notification system</notifiers>`

Logic Manager
~~~~~~~~~~~~~

* **lm-cmd** manages :doc:`/lm/lm`
* **lm-rules** separate app for the :doc:`decision rules</lm/decision_matrix>`
  management
* **lm-notifier** configures LM PLC :doc:`notification system</notifiers>`

SCADA Final Aggregator
~~~~~~~~~~~~~~~~~~~~~~

* **sfa-cmd** manages :doc:`/sfa/sfa`
* **sfa-notifier** configures SFA :doc:`notification system</notifiers>`

Other
~~~~~

* **test-uc-xc** a special app to test UC :doc:`item scripts</item_scripts>`.
  Launches an item script with UC :ref:`cvars<uc_cvars>` and EVA paths set in
  the environment.

:doc:`Virtual item</virtual>` management is being performed using
**xc/evirtual** application.

Device control apps
-------------------

EVA distribution includes preinstalled samples for the device controlling. All
sample scripts are located in **xbin** folder

TCP/IP controlled relays
~~~~~~~~~~~~~~~~~~~~~~~~

* **EG-PM2-LAN** controls `EG-PM2-LAN Smart PSU
  <http://energenie.com/item.aspx?id=7557>`
* **SR-201** controls the SR-201 relay controllers - a quite popular and simple
  solution with TCP/IP management option

1-Wire
~~~~~~

* **w1_ds2408** controls `Dallas
  DS2408 <https://datasheets.maximintegrated.com/en/ds/DS2408.pdf>_`-based
  relays on the local 1-Wire bus
* **w1_therm** monitors `Dallas DS18S20 <https://datasheets.maximintegrated.com/en/ds/DS18S20.pdf>`_, DS18B20 and other compatible temperature sensors on the local 1-Wire bus
* **w1_ls** displays the devices connected to the local 1-Wire bus
