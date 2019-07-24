Logic cycles
************

:doc:`/lm/lm` allows to define logic cycles. Logic cycle is a loop which run
specified :doc:`macro<macros>` as a worker with a chosen interval.

:doc:`/lm/lm` can create new cycles, start, stop them and reset their stats.
Cycle information is replicated to :doc:`/sfa/sfa` nodes, however SFA can
access logic cycles read-only.

Cycle control from SFA nodes (and UI) is possible only by calling pre-made LM
PLC macros, which can use :ref:`macro control functions<macro_api_start_cycle>`
to manage cycles.

.. note::

    For the heavy industry processes we strongly recommend to use dedicated
    hardware production cycle controllers and control/monitor them using EVA
    ICS as a supervisor only.

Cycle creation
==============

Cycles can be created with either LM API
:ref:`create_cycle<lmapi_create_cycle>` function or with :doc:`EVA
shell</cli>`.

To configure cycle you may specify action and interval, or you may set cycle
parameters one-by-one after the cycle is created.

To specify action and interval during cycle creation, use the following format:

.. code:: bash

    cycle create <cycle_id> [action] [interval <seconds>]

Example, start unit *unit:lamp/lamp1* (call *start* macro function) with
interval 0.5 seconds.

.. code:: bash

    cycle create cycle1 @start('unit:lamp/lamp1') interval 0.5

Another example, run macro *macro1* every 100 milliseconds:

.. code:: bash

    cycle create cycle2 macro1(1, 2, x=test) interval 0.1

.. note::

    Cycle ID must be unique within a :doc:`/lm/lm`.

Cycle configuration
===================

Each lcycle object has the following parameters:

* **autostart** cycle will start automatically as soon as LM PLC server is
  started

* **avg** (read-only) real average cycle interval

* **ict** interval correction. LM PLC will try correcting cycle interval every
  *ict* iterations to keep it real-time as max as possible. Additionally,
  during the correction LM PLC will replicate cycle state (iterations, avg)
  with connected SFA nodes (cycle *status* is replicated in real-time)

* **iterations** (read-only) cycle iterations since the last start/stats reset

* **interval** cycle interval, in seconds

* **macro** :doc:`macro<macros>`, which is called as a worker

* **on_error** :doc:`macro<macros>`, which is called if cycle error has been
  occurred

* **status** (read-only) cycle status, changed when start/stop commands are
  executed. Can be:
  
    * **0** cycle is stopped
    * **1** cycle is running
    * **2** cycle got "stop" command and will stop as soon as current iteration
      finish

* **value** (read-only) contains *iterations* and *avg* values, comma separated


.. note::

    When cycle is running, attempts to change parameters **ict**, **interval**
    or **macro** will return an error.

on_error macro
==============

Macro, defined in *on_error* cycle property is called when:

* **exception** worker macro raised an exception, *on_error* macro args
  contain:

  * **_1** *"exception"* word
  * **_2** exception object

* **timeout**/**exec error** macro execution took more time than cycle loop
  interval is set to, or worker macro exited with non-zero code. *on_error*
  macro args contain:

  * **_1** *"timeout"* or *"exec_error"* word
  * **_2** serialized worker macro execution result

the macro can e.g. stop cycle execution, send critical event to controller core
or just log an error and let cycle continue.

Performance
===========

Theoretically, cycle interval can be up to 1ms (1kHz worker frequency), but
don't expect stable cycle loops on a slow/busy hardware. In real life, software
controllers handle well production loops up to 200/300ms (3-5Hz), with lower
values (~100ms = 10Hz) users may expect 2-3% of iteration loss. Stable
logic-rich cycles with the interval, lower than 20ms (50Hz), are nearly
impossible.

If worker macro perform a calls between EVA ICS nodes, don't forget about
network timeouts.

To let cycle run with a maximum precision and avoid timeout errors, it is
strongly recommended for the low-interval cycles:

* set up dedicated LM PLC instance

* turn off controller logging

* turn off controller action history (set *keep_action_history* to 0)
  
* if worker macro performs calls to :doc:`/uc/uc`, make sure controlled unit
  state isn't replicated to other nodes in real-time via
  :doc:`notifiers</notifiers>` or stored in any state history databases (make
  dedicated group for such units and don't subscribe notifiers to it)

* read :doc:`common recommendations about using EVA ICS in high-load
  environments</highload>`.


Cycles vs jobs
==============

Both cycles and :doc:`</lm/jobs>` do similar functions: start macros with the
specified interval.

**When you should use cycles**

* you need to have complete control and monitoring on the interval loop
* you need to periodically stop / start interval loop manually
* interval is in seconds or milliseconds

usage example: automation loops.

**When jobs are better**

* you need a simple instrument to run the task periodically
* you need to start a task with the specified time schedule, e.g. every day at
  9:00
* interval is in seconds, minutes or hours, precision is not important

usage examples: statistic tasks, cleaners, system checkers.

