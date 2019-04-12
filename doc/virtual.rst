Virtual items
*************

:doc:`/uc/uc` items may be either virtual or real. You may toggle the item by
changing configuration while the server is running.

Virtual drivers
===============

If you want to build a virtual setup, the best idea is to use virtual
:doc:`drivers</drivers>` . EVA ICS distribution includes 2 virtual drivers
which cover all typical needs:

* **vrtrelay** Virtual relay driver
* **vrtsensors** Virtual sensor pool driver

Both drivers work like the real ones so it's not necessary to set the item to
virtual. When using virtual drivers, set item option *virtual=false*.

