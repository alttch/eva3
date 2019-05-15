Scheduled jobs
**************

Scheduled jobs are similar to :doc:`decision-making rules<decision_matrix>`
except they're triggered when the specified time comes.

To manage scheduled jobs you may use **eva lm** (*lm-cmd*) :doc:`console
applications</cli>`, :doc:`lm_api` functions or an appropriate :doc:`lm_ei`
interface section.

Jobs configuration is stored in **runtime/lm_job.d/** folder.

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

