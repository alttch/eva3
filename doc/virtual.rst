Virtual items
*************

:doc:`/uc/uc` items may be either virtual or real. You may toggle the item by
changing configuration while the server is running.

Virtual drivers
===============

If you want to build a virtual setup, the best idea is to use virtual
:doc:`drivers</drivers>`. EVA ICS distribution includes 2 virtual PHIs
(drivers) which cover all typical needs:

* **vrtrelay** Virtual relay driver
* **vrtsensors** Virtual sensor pool driver

Both PHIs work like the real ones, so all you need to switch your setup to
production - assign "real" drivers to items or just load "real" PHIs with the
same IDs.
