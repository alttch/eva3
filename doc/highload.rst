High-load environments
**********************

Tuning EVA ICS
==============

To use EVA ICS in high-load environments, remember the following:

* Always turn off debug mode. Debug mode significantly slows down all EVA ICS
  components.

* Make sure no :doc:`notifiers</notifiers>` are subscribed to the frequently
  (more than ~10 times per second) updated item states. If you need to
  synchronize states of such items, reduce remote controller reload intervals
  instead but set them higher than 1 second.

* Unsubscribe notifiers from INFO log messages and actions

* Replace *db-updates: instant* in :doc:`/uc/uc` configurations with *on_exit*
  or *manual*.

* If instant state database updates are strongly required, switch to MySQL or
  PostgreSQL (use option *db* instead of *db-file* in controller config).

* If you don't need action history, set *keep-action-history* in controllers'
  configuration to zero to disable it.

* Turn off logging (comment *log-file* property in configuration file) and
  reduce *keep-logmem* value.

* Increase logging level to *warning* or *error* using *logging-level* config
  option in [server] section.

* If you use passive updates, set *polldelay* to the minimal value
  (*0.001* - *0.005* for 1-5ms)

* Set *retain_enabled* to *false* for MQTT notifiers

* If HTTP API respond too slow, try increasing value of *thread-pool* option in
  [webapi] config section.

* Modbus slave and some utility workers use twisted reactor thread pool. In
  case the software reacts or performs regular tasks slowly, but system load is
  still low, try increasing value of *reactor-thread-pool* option in [server]
  section.

* If item states should be collected from the equipment which doesn't send
  events (e.g. Ethernet/IP, Modbus slaves, SNMP without traps), it's
  recommended to use :doc:`data pullers<datapullers>`.

* To speed up event synchronization between controllers, switch to :ref:`lurp`.

* The good idea is also to reduce event real-timing and use :ref:`bulk_notify`.

Hardware
========

Thanks to EVA ICS architecture and optimization for modern multi-core CPUs, the
platform can provide good results even on a microcomputers. System components
and :doc:`CLI</cli>` tools may require more time to launch on architectures
different than Intel x86_64, but the regular performance should not be affected
even on an embedded ARM-based systems.

According to tests, EVA ICS can show bad performance (slow startup/shutdown) on
industrial and micro computers if they have:

* small amount of RAM (minimum 512 MB is recommended)
* slow SSD drive or SD card.

We strongly recommend using at least UHS-I SD cards which can show a speed up
to 100 MB/s.

.. _benchmarks:

Benchmarks
==========

Benchmark tests for :doc:`/uc/uc` can be performed with
*tests/benchmark-uc-crt* tool. Benchmark results may be different on a systems
with different background load, so please stop all unnecessary processes
before starting a test.

The primary parameter for UC which is benign benchmarked is a time, required for
the controller to:

* obtain :doc:`item</items>` state from :doc:`driver</drivers>`

* perform a simple in-core event handling (convert item value to float and then
  compare with a float number) with self thread-locking

* get action request from event handler and execute it using another driver

The time between a moment when the first driver gets new item value and a
moment when the second driver is ready to call equipment action is named
**Core Reaction Time (CRT)**.

The benchmark tool for :doc:`/uc/uc` turns on internal controller benchmark,
performs 1000 CRT tests with 30ms delays on a single sensor/unit pair and
displays the average CRT value in milliseconds.

The benchmark is performed on virtual drivers, so the actual system reaction
time may be higher than CRT, depending on the equipment connected.

.. warning::

    It's not recommended to perform a real benchmarking tests on SOHO and light
    industry relays due to their limited lifetime (~100-200k switches)

Below are benchmark results on a test systems (lower CRT is better):

+--------------------+-------------------------------+-------+------------------+-----------+
| System             |           CPU                 | Cores | EVA ICS          |  CRT, ms  |
+====================+===============================+=======+==================+===========+
| VMWare ESXi 5.5    | Intel Xeon E5630 2.53GHz      | 1     | 3.1.1 2018101701 | 4.5       |
+--------------------+-------------------------------+-------+------------------+-----------+
| VMWare ESXi 5.5    | Intel Xeon E5630 2.53GHz      | 4     | 3.1.1 2018101701 | 3         |
+--------------------+-------------------------------+-------+------------------+-----------+
| VMWare ESXi 5.5    | Intel Xeon D-1528 1.90GHz     | 1     | 3.1.1 2018101701 | 5         |
+--------------------+-------------------------------+-------+------------------+-----------+
| VMWare ESXi 5.5    | Intel Xeon D-1528 1.90GHz     | 4     | 3.1.1 2018101701 | 3.5       |
+--------------------+-------------------------------+-------+------------------+-----------+
| Supermicro X9SXX   | Intel Xeon E3-1230 V2 3.30GHz | 8     | 3.1.1 2018101701 | 4         |
+--------------------+-------------------------------+-------+------------------+-----------+
| Supermicro E100    | Intel Atom E3940 1.60GHz      | 4     | 3.1.1 2018101701 | 8.5       |
+--------------------+-------------------------------+-------+------------------+-----------+
| Raspberry Pi 1A    | ARMv6 rev 7 v6l               | 1     | 3.1.1 2018101701 | 110       |
+--------------------+-------------------------------+-------+------------------+-----------+
| Raspberry Pi 2B    | ARMv7 rev 5 v7l               | 4     | 3.1.1 2018101701 | 22.5      |
+--------------------+-------------------------------+-------+------------------+-----------+
| Raspberry Pi 3B+   | ARMv7 rev 4 v7l               | 4     | 3.1.1 2018101701 | 21        |
+--------------------+-------------------------------+-------+------------------+-----------+
| UniPi Axon S115    | ARMv8 Cortex-A53              | 4     | 3.1.1 2018101701 | 27        |
+--------------------+-------------------------------+-------+------------------+-----------+

*According to tests, EVA ICS 3.2 is about 15% faster than 3.1.1*

