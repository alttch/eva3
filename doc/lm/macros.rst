Logic control macros
====================

In :doc:`lm` macros can be triggered on the list of events, third-party
applications or user via :doc:`LM EI<lm_ei>` interface or :doc:`LM API<lm_api>`
functions.

Macro code is located the file written in Python and located in the folder
**xc/lm/** under the name <macro_id>.py, i.e. *test.py* for "test" macro. Macro
id should be unique within the single LM PLC, full id (group/id) - within the
whole installation.

Additionally, each macro is automatically appended with **common.py** file
located in the same folder enabling to quickly assign common functions to
several macros without using modules.

Macros are compiled into byte-code each time after macros file or **common.py**
file are changed. Compilation or execution errors can be viewed in the log
files of the controller.

.. contents::

Executing macros
----------------

To execute a macro, use **run** command of :doc:`lm-cmd</cli>` or LM API
:ref:`run<lm_run>` function.

Debugging macros
----------------

Macro compilation and execution errors are written into the logs of the
controller on DEBUG level, the exceptions are also added to **err** field of
the execution result.

To receive information about an errors you may run the following command:

.. code-block:: bash

    lm-cmd run -i <macro_id> -w 3600 | grep -v ^Exec | jq -r .err

Macros configuration
--------------------

After the macro code is placed into *xc/lm/<macro_id>.py* file, it should be
appended to the controller using :ref:`create_macro<lm_create_macro>` LM API
function or with **lm-cmd**.

After the macro configuration is created, you may view it's params using
:ref:`list_macro_props<lm_list_macro_props>` and change them with
:ref:`set_macro_prop<lm_set_macro_prop>`.

Parameters:

* **id** macros id, can't be modified after the macro is created
* **action_enabled** *true* means macro can be executed (true by default)
* **action_exec** controller gets the code of the macro from the file
  *<macro_id>.py* by default, use this parameter to assign another file
* **description** macro description
* **group** macro group (in difference to other objects, macro group can be
  changed after creation)
* **pass_errors** if *true*, in case the function called by macro is completed
  with an exception, the controller ignores this and continues the code
  execution (false by default)

Common principles of macros operation
-------------------------------------

Macros are launched simultaneously: system does not wait for the completion of
the macro and launches its next copy or another macro in parallel. If you want
only one copy of macro to operate at the certain point of time or to block
execution of the other macros, use macro :ref:`lock<m_lock>` and
:ref:`unlock<m_unlock>` functions.

The system architecture does not provide the possibility to stop macro from
outside, that is why macros should have minimum internal logic and cycles.

All the logic should be implemented in the :doc:`decision-making
matrix<decision_matrix>`. The working cycles should be implemented with
:ref:`logic variables<lvar>` timers.

System macros
-------------

If defined, macro named **system/autoexec** is launched automatically at the
controller startup. This macro is not always the first one executed, as far as
some initial :doc:`decision-making rules<decision_matrix>` may call assigned
macros, or some events may be handled before. In case macro is launched later
than :ref:`logic variables<lvar>` or other loadable items update their status
(e. g. due to slow connection with :ref:`MQTT server<mqtt_>`) it's recommended
to use :ref:`sleep<m_sleep>` function to do a small delay.

Macros from **system** group are considered as the local system macros and
aren't synchronized to :doc:`SFA</sfa/sfa>`.

Example of **autoexec** macro usage:

.. code-block:: python

    # both cycle timers are expired
    if is_expired('timers/timer1') and is_expired('timers/timer2'):
        # launch the first cycle process
        action('pumps/pump1', on)
        # start the first cycle timer
        reset('timers/timer1')

Macros and security
-------------------

As all Python features are available for the macros, including the execution of
the external programs or working with any local files, code of the macros
should be edited only by the system administrator.

If access permissions to the individual macros are configured via API keys, you
should take into account the following: if macro runs other macros using
:ref:`run<m_run>` function, these macros will be executed even if the API key
allows to run only the initial macro.

Macros built-ins
----------------

Macros can execute any Python functions or use Python modules installed on the
local server. In addition, macros have a set of the built-in functions and
variables.

Built-in functions are include for quick access of the most frequently used
Python functions as well as :doc:`lm_api` and :doc:`/uc/uc_api`. When calling
API function, item id is always transmitted in full. When calling other macros
and working with logic variables, it's possible to use the short ids only.

Variables
---------

Macros have the following built-in variables:

* **on** alias to integer *1*
* **off** alias to integer *0*
* **yes** alias to boolean *True*
* **no** alias to boolean *False*

* **_source** item generated the :doc:`event<decision_matrix>`, used by the
  system to call the macro. You may directly access the item and i.e. use it's
  internal variables such as *_source.item_id*, *_source.full_id*,
  *_source.oid* etc.
* **argv** array list of arguments the macro is being executed with
* **_0** current macro id (i.e. *'test'*)
* **_00** current macro full id (i.e. *'group1/test'*)
* **_1, _2, ... _9** first 9 arguments the macro is being executed with
* **lm_cvars** all :ref:`lm_cvars<lm_cvars>` variables
* **out** macro may use this variable to output the data which will be set to
  **out** field of the execution result

.. note::

    if macro arguments or lm_cvars are numbers, they are automatically converted
    to float type


Log messaging functions
-----------------------

Macros may send messages to the log of the controller with the following
functions:

* **debug(msg)** send DEBUG level message
* **info(msg)** send INFO level message
* **warning(msg)** send WARNING message
* **error(msg)** send ERROR message
* **critical(msg)** send  CRITICAL message

In addition, **print** function is an alias of **info**.

Shared variables
----------------

Apart from the :ref:`logic variables<lvar>` macros, can exchange variables
within the single controller with the following functions:

* **shared(varname)** get value of the shared variable
* **set_shared(varname, value)** set value of the shared variable

Shared variables are not saved in case the controller is restarted.

Locking features
----------------

These functions implement internal locking which may be used i.e. to block
other macros to run until the current one is finished.

.. _m_lock:

lock - lock token request
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    lock(lock_id, timeout=None, expires=None)

params:

* **lock_id** unique lock id (defined by user)
* **timeout** lock request timeout (in seconds)
* **expires** time (seconds) after which lock is automatically released

Returns *True*, if lock has been requested successfully, *False* in case of the
failure.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the locking wasn't successful.

.. _m_unlock:

unlock - release lock token
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    unlock(lock_id)

params:

* **lock_id** unique lock id (defined by user)

Unlike the SYS API :ref:`unlock<s_unlock>` function, this one always returns
*True*, even if lock doesn't exist.

Item functions
--------------

The following functions are used to control the :doc:`items</items>`:

lvar_status - get logic variable status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    lvar_status(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns status (integer) of logic variable, *None* if variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

lvar_value, value - get logic variable value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    lvar_value(lvar_id)
    # is equal to
    value(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns value (float if the value is numeric) of logic variable, *None* if
variable is not found. If the value is *null*, returns an empty string.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

set - set logic variable value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    set(lvar_id, value=None)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)
* **value** value to set. If not specified, variable is set to *null*

Returns *True* on success, *False* if variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

.. _m_clear:

clear - stop timer/flag clear
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If lvar is being used as a timer and has **expires** set, this function sets
it's status to *0* which works like a timer stop.

If lvar is being used as a flag and has no expiration, this sets it's value to
*0* which works like setting flag to *False*

.. code-block:: python

    clear(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns *True* on success, *False* if variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

toggle - toggle a flag value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sets lvar value to *1* if it has value *"0"*, otherwise *"1"*. If lvar is being
used as a flag, this works like a switching between *False* and *True*.

.. code-block:: python

    toggle(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns *True* on success, *False* if variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

expires - set the lvar expiration time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Function is used to set/change lvar expiration time and is useful for changing
timers' durations.

.. code-block:: python

    expires(lvar_id, etime=0)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)
* **etime** new expiration time (in seconds)

If expires is not defined or set to zero, the function stops a timer, but apart
from :ref:`clear<m_clear>` completely disables a timer by setting it's
expiration to 0. To return the timer back to work, set it's expiration time
back after the timer reset (not before!).

Returns *True* on success, *False* if variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

is_expired - check timer expiration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Function is useful when lvar is being used as a timer to quickly check is it
still running or not.

.. code-block:: python

    is_expired(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns *True* if lvar has expired status (timer is finished), equal to checking
*status==1 and value==''*, *False* if lvar is not expired or not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

unit_status - get unit status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    unit_status(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns status (integer) of unit, *None* if unit is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

unit_value - get unit value
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    unit_value(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns value (float if the value is numeric) of unit state, *None* if unit is
not found. If the value is *null*, returns an empty string.  Returns value
(integer) of unit, *None* if unit is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

unit_nstatus - get unit future status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    unit_nstatus(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns future status (integer) of unit, *None* if unit is not found. If the
unit has no action running, future status is equal to the current.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

unit_nvalue - get unit future value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    unit_nvalue(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns value (float if the value is numeric) of unit state, *None* if unit is
not found. If the value is *null*, returns an empty string.  Returns value
(integer) of unit, *None* if unit is not found. If the unit has no action
running, future state value is equal to the current.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

is_busy - check if the unit has action running
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compares current and future unit state, the difference means the unit currently
is running an action and is busy.

.. code-block:: python

    is_busy(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns *True* if unit is currently running an action and its future state is
different from the current. *False* if states are equal and it means unit has
no action running, *None* if unit is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

action, start, stop - start unit action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Starts the action for the unit.

.. code-block:: python

    action(unit_id, status, value=None, wait=0, uuid=None, priority=None)
    # same as action with status=1
    start(unit_id, value=None, wait=0, uuid=None, priority=None)
    # same as action with status=0
    stop(unit_id, value=None, wait=0, uuid=None, priority=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)
* **status** unit new status
* **value** unit new value
* **wait** wait (seconds) for the action execution
* **uuid** set action uuid (generated automatically if not set)
* **priority** action priority on the controller (default 100, lower value
  means higher priority)

Returns result in the same dict format as UC API :ref:`action<uc_action>`
function, *None* if unit is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

result - get action result
~~~~~~~~~~~~~~~~~~~~~~~~~~

Obtain action result, either all results for the unit by **unit_id** or the
particual action result by **uuid**

.. code-block:: python

    result(unit_id=None, uuid=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)
* **uuid** action uuid

Either **unit_id** or **uuid** must be specified. The controller can obtain the
result by uuid only if the action was executed by its API or macro function and
the controller hasn't been restarted after that.

Returns result in the same dict format as UC API :ref:`result<uc_result>`
function, *None* if unit is not found or controller doesn't know about the
action with the specified uuid.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

.. note::

    macro **result** function returns the execution result of unit action,
    while :ref:`result<lm_result>` function of LM API returns the execution
    results of local macros only.

terminate - terminate the current action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Terminate the current unit action, either by **unit_id** or the by action
**uuid**

.. code-block:: python

    terminate(unit_id=None, uuid=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)
* **uuid** action uuid

Either **unit_id** or **uuid** must be specified. The controller can terminate
the action by uuid only if it was executed by its API or macro function and the
controller hasn't been restarted after that.

Returns termination result in the same dict format as UC API
:ref:`terminate<uc_terminate>` function, *None* if unit is not found, the
controller doesn't know about the action with the specified uuid or the remote
action doesn't exist (or is already finished).

Doesn't raise any exceptions.

q_clean - clean unit action queue
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cleans the unit action queue but keeps the current action running if it already
has been started.

.. code-block:: python

    q_clean(unit_id=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns queue clean result in the same dict format as UC API
:ref:`q_clean<uc_q_clean>` function, *None* if unit is not found.

Doesn't raise any exceptions.

kill - clean unit queue and terminate current action
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Cleans the unit action queue and terminates the current action running if it
already has been started.

.. code-block:: python

    kill(unit_id=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns queue clean result in the same dict format as UC API
:ref:`kill<uc_kill>` function, *None* if unit is not found.

Doesn't raise any exceptions.

sensor_status - get sensor status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    sensor_status(sensor_id)

params:

* **sensor_id** :ref:`sensor<sensor>` id (full)

Returns status (integer) of sensor, *None* if sensor is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the sensor is not found.

sensor_value - get sensor value
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    sensor_value(sensor_id)

params:

* **sensor_id** :ref:`sensor<sensor>` id (full)

Returns value (float if the value is numeric) of sensor state, *None* if sensor
is not found. If the value is *null*, returns an empty string.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the sensor is not found.

System functions
----------------

.. _m_sleep:

sleep - pause operations
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # alias for python time.sleep
    sleep(seconds.milliseconds)


mail - send email message
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    mail(subject=None, text=None, rcp=None)

params:

* **subject** email subject
* **text** email text
* **rcp** recipient or array of the recipients

The function use **[mailer]** section of the :ref:`LM PLC
configuration<lm_ini>` to get sender address and list of the recipients (if not
specified).

Returns *True* if the message is sent successfully.

get - HTTP/GET request
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # alias for requests.get
    get(uri, args)

See `requests <http://docs.python-requests.org/en/master/>`_ documentation for
more info.

post - HTTP/POST request
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # alias for requests.post
    post(uri, args)

See `requests <http://docs.python-requests.org/en/master/>`_ documentation for
more info.

system - execute OS command
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # alias for python os.system
    system(command)


.. _m_cmd:

cmd - execute command script
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Executes a :ref:`command script<cmd>` on the chosen controller.

.. code-block:: python

    cmd(controller_id, command, args=None, wait=None, timeout=None)

params:

* **controller_id** controller id where the script is located (full or short)
* **command** script command name
* **args** script command arguments (array or separated with spaces in a
  string)
* **wait** wait for the command result (in seconds)
* **timeout** max command execution time

Returns the result equal to the result of SYS API :ref:`cmd<s_cmd>` function.

.. _m_run:

run - execute another local macro
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    run(macro_id, argv=None, wait=0, uuid=None, priority=None)

params:

* **macro_id** local macro id (full or short)
* **argv** execution arguments
* **wait** wait (in seconds) for the result
* **uuid** macro action uuid (generated automatically if not set)
* **priority** action priority (default 100, lower value means higher priority)

Returns the result equal to the result of LM API :ref:`run<lm_run>` function.

exit - exit macro
~~~~~~~~~~~~~~~~~

Finishes macro execution

.. code-block:: python

    exit(code=0)

params:

* **code** macro exit code (0 - no errors)
