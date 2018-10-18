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

* Replace *db_updates = instant* in :doc:`/uc/uc` configurations with *on_exit*
  or *manual*.

* If you don't need action history, set *keep_action_history* in controllers'
  configuration to zero to disable it.

* Turn off logging (comment *log_file* property in configuration) and reduce
  *keep_logmem* value.

* If you use passive updates, set *polldelay* to the minimal value
  (*0.001* - *0.005* for 1-5ms)

Hardware
========

EVA ICS is written in Python 3. It is not the fastest programming language in
the world, but thanks to EVA ICS architecture and optimization for modern
multi-core CPUs, the platform can provide good results even on a
microcomputers. System components and :doc:`CLI</cli>` tools may require more
time to launch on architectures different than Intel x86_64, but the regular
performance should not be affected even on an embedded ARM-based systems.

.. _benchmarks:

Benchmarks
==========

Benchmark tests for :doc:`/uc/uc` can be performed with
*tests/benchmark-uc-crt* tool. Benchmark results may be different on a systems
with different background load, so please stop all unnecesseary processes
before starting a test.

The primary parameter for UC which's bening benchmarked is a time, required for
the controller to:

* obtain :doc:`item</items>` state from :doc:`driver</drivers>`

* perform a simple in-core event handling (convert item value to float and then
  compare with a float number) with self thread-locking

* get action requiest from event handler and execute it using another driver

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

+--------------------+---------------------------------+-------+-----------+
| System             |           CPU                   | Cores |  CRT, ms  |
+====================+=================================+=======+===========+
| VMWare ESXi 5.5    | Intel Xeon D-1528 (1.90GHz)     | 1     | 5         |
+--------------------+---------------------------------+-------+-----------+
| VMWare ESXi 5.5    | Intel Xeon D-1528 (1.90GHz)     | 4     | 3.5       |
+--------------------+---------------------------------+-------+-----------+
| Supermicro X9SXX   | Intel Xeon E3-1230 V2 (3.30GHz) | 8     | 4         |
+--------------------+---------------------------------+-------+-----------+
| Raspberry Pi 2B    | ARMv7 rev 5 (v7l)               | 4     | 22.5      |
+--------------------+---------------------------------+-------+-----------+
