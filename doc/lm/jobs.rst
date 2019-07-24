Scheduled jobs
**************

Scheduled jobs are similar to :doc:`decision-making rules<decision_matrix>`
except they're triggered when the specified time comes.

To manage scheduled jobs you may use **eva lm** (*lm-cmd*) :doc:`console
applications</cli>`, :doc:`lm_api` functions or an appropriate :doc:`lm_ei`
interface section.

Jobs configuration is stored in **runtime/lm_job.d/** folder.

Job creation
============

Jobs can be created with either LM API :ref:`create_job<lmapi_create_job>`
function or with :doc:`EVA shell</cli>`.

To configure job you may specify action and schedule, or you may set job
parameters one-by-one after the job is created.

To specify action and schedule during job creation, use the following format.
Note that controller doesn't check does condition item and/or macro exist on
the moment of job creation:

.. code:: bash

    job create [action] [every <schedule>]

Example, start unit *unit:ventilation/v1* (call *start* macro function) every 5
minutes.

.. code:: bash

    job create @start('unit:ventilation/v1') every 5 minutes

Another example, run macro *macro1* every hour
minutes.

.. code:: bash

    job create macro1(1, 2, x=test) every hour

.. note::

    New job is always created as "disabled" and you must enable it with "job
    enable" CLI command or call LM API function
    :ref:`set_job_prop<lmapi_set_job_prop>`, setting *enabled=True*.

Job configuration
=================

* **description** job description

* **enabled** if *True*, job is enabled (new jobs are disabled by default)

* **every** schedule interval

* **macro** :doc:`macro<macros>` that is executed

* **macro_args** arguments the macro is executed with

* **macro_kwargs** keyword arguments the macro is executed with

Job schedule interval
=====================

Schedule interval (*every* parameter) is set in a human-readable format.
Examples:

* **second** execute job every second
* **5 seconds** execute job every 5 seconds
* **2 minutes at :30** execute job every 2 minutes at 30th second
* **5 hours** execute job every 5 hours
* **2 days** execute job every 2 days
* **wednesday at 13:15** execute job every Wednesday at 13:15

