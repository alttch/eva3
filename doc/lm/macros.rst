Logic control macros
********************

In :doc:`lm` macros can be triggered on the list of events, third-party
applications or user via :doc:`LM EI<lm_ei>` interface or :doc:`LM API<lm_api>`
functions.

Macro code is a file written in Python and located in the folder **xc/lm/**
under the name <macro_id>.py, i.e. *test.py* for "test" macro. Macro id should
be unique within the single LM PLC, full id (group/id) - within the whole
installation.

Additionally, each macro is automatically appended with **common.py** file
located in the same folder enabling to quickly assign common functions to
several macros without using modules.

Macros are compiled into byte-code each time after macros file or **common.py**
file are changed. Compilation or execution errors can be viewed in the log
files of the controller.

.. contents::

Executing macros
================

To execute a macro, use **macro run** command of :doc:`lm-cmd</cli>` or LM API
:ref:`run<lm_run>` function.

Debugging macros
================

Macro compilation and execution errors are written into the logs of the
controller on DEBUG level, the exceptions are also added to **err** field of
the execution result.

To receive information about errors you may run the following command:

.. code-block:: bash

    lm-cmd -J run <macro_id> -w 3600 | jq -r .err

Macros configuration
====================

After the macro code is placed into *xc/lm/<macro_id>.py* file, it should be
appended to the controller using :ref:`create_macro<lm_create_macro>` LM API
function or with **lm-cmd**.

After the macro configuration is created, you may view its params using
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
=====================================

Macros are launched simultaneously: system does not wait for the completion of
the macro and launches its next copy or another macro in parallel. If you want
only one copy of macro to operate at the certain point of time or to block
execution of other macros, use macro :ref:`lock<m_lock>` and
:ref:`unlock<m_unlock>` functions.

The system architecture does not provide the possibility to stop macro from
outside, that is why macros should have minimum internal logic and cycles.

All the logic should be implemented in the :doc:`decision-making
matrix<decision_matrix>`. The working cycles should be implemented with
:ref:`logic variables<lvar>` timers.

System macros
=============

If defined, macro named **system/autoexec** is launched automatically at the
controller startup. This macro is not always the first one executed, as far as
some initial :doc:`decision-making rules<decision_matrix>` may call assigned
macros, or some events may be handled before. In case a macro is launched later
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
===================

As all Python features are available for macros, including execution of
external programs or working with any local files, the code of macros should be
edited only by system administrator.

If access permissions to individual macros are configured via API keys, you
should take into account the following: if a macro runs other macros using
:ref:`run<m_run>` function, these macros will be executed even if the API key
allows to run only the initial macro.

Macros built-ins
================

Macros can execute any Python functions or use Python modules installed on the
local server. In addition, macros have a set of built-in functions and
variables.

Built-in functions are included for quick access to the most frequently used
Python functions such as :doc:`lm_api` and :doc:`/uc/uc_api`. When calling
API function, item id is always transmitted in full. When calling other macros
and working with logic variables, it's possible to use the short ids only.

Variables
=========

Macros have the following built-in variables:

* **on** alias to integer *1*
* **off** alias to integer *0*
* **yes** alias to boolean *True*
* **no** alias to boolean *False*

* **_source** item generated the :doc:`event<decision_matrix>`, used by the
  system to call the macro. You may directly access the item and e.g. use its
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
=======================

Macros may send messages to the log of the controller with the following
functions:

* **debug(msg)** send DEBUG level message
* **info(msg)** send INFO level message
* **warning(msg)** send WARNING message
* **error(msg)** send ERROR message
* **critical(msg)** send  CRITICAL message

In addition, **print** function is an alias of **info**.

Shared variables
================

Apart from the :ref:`logic variables<lvar>` macros, can exchange variables
between each other within the single controller with the following functions:

* **shared(varname, default_value)** get value of the shared variable or return
  *default_value* if shared variable doesn't exist

**set_shared(varname, value)** set value of the shared variable

Shared variables are not saved in case the controller is restarted.

Locking features
================

These functions implement internal locking which may be used e.g. to block
other macros to run until the current one is finished.

.. _m_lock:

lock - lock token request
-------------------------

.. code-block:: python

    lock(lock_id, timeout=None, expires=None)

params:

* **lock_id** unique lock id (defined by user)
* **timeout** lock request timeout (in seconds)
* **expires** time (seconds) after which the lock is automatically released

Returns *True*, if lock has been requested successfully, *False* in case of
failure.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the locking wasn't successful.

.. _m_unlock:

unlock - release lock token
---------------------------

.. code-block:: python

    unlock(lock_id)

params:

* **lock_id** unique lock id (defined by user)

Returns *True* if the lock is unlocked, *False*, if the lock does not exist.

Item functions
==============

The following functions are used to control the :doc:`items</items>`:

lvar_status - get logic variable status
---------------------------------------

.. code-block:: python

    lvar_status(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns status (integer) of logic variable, *None* if the variable is not
found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

lvar_value, value - get logic variable value
---------------------------------------------

.. code-block:: python

    lvar_value(lvar_id, default='')
    # is equal to
    value(lvar_id, default='')

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns value (float if the value is numeric) of logic variable, *None* if
variable is not found. If the value is *null*, returns an empty string by
default or *default* value if specified.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

.. note::

    You may use **value** function to return sensor or unit values specifying
    their OIDs

set - set logic variable value
------------------------------

.. code-block:: python

    set(lvar_id, value=None)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)
* **value** value to set. If not specified, variable is set to *null*

Returns *True* on success, *False* if the variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

.. _m_clear:

clear - stop timer/flag clear
-----------------------------

If lvar is being used as a timer and has **expires** set, this function sets
its status to *0* which works like a timer stop.

If lvar is used as a flag and has no expiration, this sets its value to *0*
which works like setting flag to *False*

.. code-block:: python

    clear(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns *True* on success, *False* if the variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

toggle - toggle a flag value
----------------------------

Sets lvar value to *1* if it has value *"0"*, otherwise *"1"*. If lvar is used
as a flag, this works like a switching between *False* and *True*.

.. code-block:: python

    toggle(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns *True* on success, *False* if the variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

.. code-block :: python

    # You may use this function to toggle unit status  specifying its OID:
    toggle(unit_oid, wait=0, uuid=None, priority=None)

expires - set the lvar expiration time
--------------------------------------

Function is used to set/change lvar expiration time and is useful for changing
timers' durations.

.. code-block:: python

    expires(lvar_id, etime=0)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)
* **etime** new expiration time (in seconds)

If expiry is not defined or set to zero, the function stops the timer, but
apart from :ref:`clear<m_clear>` completely disables the timer by setting its
expiration to 0. To return the timer back to work, set its expiration time back
after the timer reset (not before!).

Returns *True* on success, *False* if the variable is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

is_expired - check timer expiration
-----------------------------------

Function is useful when lvar is used as a timer to quickly check if it's
still running or not.

.. code-block:: python

    is_expired(lvar_id)

params:

* **lvar_id** :ref:`logic variable<lvar>` id (full or short)

Returns *True* if lvar has expired status (timer is finished), equal to checking
*status==1 and value==''*, *False* if lvar is not expired or not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the variable is not found.

.. _m_status:

status - get item status
------------------------

.. code-block:: python

    status(oid)

params:

* **oid** :doc:`item</items>` oid (**type:group/id**)

Returns status (integer) of the item, *None* if the item is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the item is not found.

.. _m_value:

value - get item value
----------------------

.. code-block:: python

    value(oid)

params:

* **oid** :doc:`item</items>` oid (**type:group/id**)

Returns value (float if the value is numeric) of the item state, *None* if the
item is not found. If the value is *null*, returns an empty string.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the item is not found.

.. _m_unit_status:

unit_status - get unit status
-----------------------------

.. code-block:: python

    unit_status(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns status (integer) of the unit, *None* if the unit is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

unit_value - get unit value
---------------------------

.. code-block:: python

    unit_value(unit_id, default='')
    # is equal to
    value(unit_oid, default='')

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns value (float if the value is numeric) of the unit state, *None* if the
unit is not found. If the value is *null*, returns an empty string by
default or *default* value if specified.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

unit_nstatus - get unit future status
-------------------------------------

.. code-block:: python

    unit_nstatus(unit_id)
    # or
    nstatus(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns future status (integer) of the unit, *None* if the unit is not found.
If the unit has no action running, future status is equal to the current.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

unit_nvalue - get unit future value
-----------------------------------

.. code-block:: python

    unit_nvalue(unit_id)
    # or
    nvalue(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns value (float if the value is numeric) of the unit state, *None* if the
unit is not found. If the value is *null*, returns an empty string. . If the
unit has no action running, future state value is equal to the current.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

is_busy - check if the unit has action running
----------------------------------------------

Compares current and future unit state, the difference means the unit is
currently is running an action and is busy.

.. code-block:: python

    is_busy(unit_id)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns *True* if the unit is currently running an action and its future state
is different from the current. *False* if the states are equal and it means the
unit has no action running, *None* if the unit is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

history - get lvar state history
--------------------------------

Returns list or dict with state history records for the specified lvar(s).

.. code-block:: python

    history(lvar_id, t_start=None, t_end=None, limit=None, prop=None,
        time_format=None, fill=None, fmt=None, db=None):

params:

* **lvar_id** lvar ID, or multiple IDs, comma separated
* **t_start** time frame start, ISO or Unix timestamp
* **t_end** time frame end, optional (default: current time), ISO or Unix
  timestamp
* **limit** limit history records (optional)
* **prop** item property (**status** or **value**)
* **time_format** time format (**iso** or **raw** for Unix timestamp)
* **fill** fill frame with the specified interval (e.g. *1T* - 1 minute, *2H* -
  2 hours etc.), optional
* **fmt** output format, **'list'** (default) or **'dict'**
* **db** :doc:`notifier</notifiers>` ID which keeps history for the specified
  item(s) (default: **db_1**)

To get state history for the multiple items:

* **fill** param is required
* **fmt** should be specified as **list**

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the lvar or history database is not found.

action, action_toggle, start, stop - start unit action
------------------------------------------------------

Starts the action for the unit.

.. code-block:: python

    action(unit_id, status, value=None, wait=0, uuid=None, priority=None)
    # same as action with status=1
    start(unit_id, value=None, wait=0, uuid=None, priority=None)
    # same as action with status=0
    stop(unit_id, value=None, wait=0, uuid=None, priority=None)
    # same as start (without a value) if status=0 or stop if status=1
    action_toggle(unit_id, wait=0, uuid=None, priority=None)
    # if unit OID (unit:group/unit_id) is specified, you may use "toggle"
    # instead:
    toggle(unit_oid, wait=0, uuid=None, priority=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)
* **status** unit new status
* **value** unit new value
* **wait** wait (seconds) for the action execution
* **uuid** set action uuid (generated automatically if not set)
* **priority** action priority on the controller (default 100, lower value
  means higher priority)

Returns result in the same dict format as UC API :ref:`action<uc_action>`
function, *None* if the unit is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

result - get action result
--------------------------

Obtain action result, either all results for the unit by **unit_id** or the
particular action result by **uuid**

.. code-block:: python

    result(unit_id=None, uuid=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)
* **uuid** action uuid

Either **unit_id** or **uuid** must be specified. The controller can obtain the
result by uuid only if the action was executed by its API or macro function and
the controller hasn't been restarted after that.

Returns result in the same dict format as UC API :ref:`result<uc_result>`
function, *None* if the unit is not found or controller doesn't know about the
action with the specified uuid.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the unit is not found.

.. note::

    macro **result** function returns the execution result of the unit action,
    while :ref:`result<lm_result>` function of LM API returns the execution
    results of local macros only.

terminate - terminate the current action
----------------------------------------

Terminate the current unit action, either by **unit_id** or by action **uuid**

.. code-block:: python

    terminate(unit_id=None, uuid=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)
* **uuid** action uuid

Either **unit_id** or **uuid** must be specified. The controller can terminate
the action by uuid only if it was executed by its API or macro function and the
controller hasn't been restarted after that.

Returns termination result in the same dict format as UC API
:ref:`terminate<uc_terminate>` function, *None* if the unit is not found, the
controller doesn't know about the action with the specified uuid or the remote
action doesn't exist (or is already finished).

Does not raise any exceptions.

q_clean - clean unit action queue
---------------------------------

Cleans the unit action queue but keeps the current action running if it already
has already been started.

.. code-block:: python

    q_clean(unit_id=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns queue clean result in the same dict format as UC API
:ref:`q_clean<uc_q_clean>` function, *None* if the unit is not found.

Does not raise any exceptions.

kill - clean unit queue and terminate current action
----------------------------------------------------

Cleans the unit action queue and terminates the current action running if it
has already been started.

.. code-block:: python

    kill(unit_id=None)

params:

* **unit_id** :ref:`unit<unit>` id (full)

Returns queue clean result in the same dict format as UC API
:ref:`kill<uc_kill>` function, *None* if the unit is not found.

Does not raise any exceptions.

sensor_status - get sensor status
---------------------------------

.. code-block:: python

    sensor_status(sensor_id)

params:

* **sensor_id** :ref:`sensor<sensor>` id (full)

Returns status (integer) of sensor, *None* if the sensor is not found.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the sensor is not found.

sensor_value - get sensor value
-------------------------------

.. code-block:: python

    sensor_value(sensor_id, default='')
    # is equal to
    value(sensor_oid, default='')

params:

* **sensor_id** :ref:`sensor<sensor>` id (full)

Returns value (float if the value is numeric) of sensor state, *None* if the
sensor is not found. If the value is *null*, returns an empty string by
default or *default* value if specified.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the sensor is not found.

Rule management functions
=========================

.. _m_set_rule_prop:

set_rule_prop - set rule parameters
-----------------------------------

.. code-block:: python

    set_rule_prop(rule_id, prop, value=None, save=False)

Allows to set configuration parameters of the rule.

Parameters:

* **rule_id** rule id
* **prop** rule configuration param
* **value** param value

optionally:

* **save** If *True*, save unit configuration on disk immediately after
  creation

Device management functions
===========================

Macros can create, update and destroy :ref:`devices<device>` with pre-defined
device templates.

.. _m_create_device:

create_device - create device items
-----------------------------------

.. code-block:: python

    create_device(controller_id, device_tpl, cfg=None, save=None):

params:

* **controller_id** connected :doc:`/uc/uc` ID
* **device_tpl** device template, stored on the connected controller in
  *runtime/tpl*
* **cfg** configuration params
* **save** If *True*, save items configuration on disk immediately after
  operation

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the access error has occured.

.. _m_update_device:

update_device - update device items
-----------------------------------

Works similarly to :ref:`m_create_device` function but doesn't create new items,
updating item configuration of the existing ones.

.. code-block:: python

    update_device(controller_id, device_tpl, cfg=None, save=None):

Parameters and return data are the same.

.. _m_destroy_device:

destroy_device - destroy device items
-------------------------------------

Works in opposite way to :ref:`m_create_device` function, destroying all items
specified in the template.

.. code-block:: python

    destroy_device(controller_id, device_tpl, cfg=None)

Parameters and return data are the same except that the function doesn't have
**save** param.

File management functions
=========================

ls - list files by mask
-----------------------

.. code-block:: python

    ls(mask)

params:

* **mask** file mask to list (i.e. */var/folder1/\*.jpg*)

Returns file listing by the specified mask as an array:

.. code-block:: json

   [{
        "name": "1.png",
        "size": 2443,
        "time": {
            "c": 1507735364.2441583,
            "m": 1507734605.1451921
        }
    },
    {
        "name": "2.png",
        "size": 2231,
        "time": {
            "c": 1507735366.5561802,
            "m": 1507735342.923956
        }
    }]

where

* **size** file size (in bytes)
* **time/c** inode creation time (ctime, UNIX timestamp)
* **time/m** file modification time (mtime)

open_newest - open newest file
------------------------------

Tries to find and open the newest file by the specified mask. Useful i.e. for
the folders where security cameras periodically upload an images.

.. code-block:: python

    open_newest(mask, mode='r', alt=True)

params:

* **mask** file mask to search in (i.e. */var/folder1/\*.jpg*)
* **mode** file open mode
* **alt** open alternative (the second newest) file if there's error opening
  the newest one (i.e. when the newest file it's still uploading)

Returns a file stream.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the file can not be opened.

open_oldest - open oldest file
------------------------------

Tries to find and open the oldest file by the specified mask.

.. code-block:: python

    open_oldest(mask, mode='r')

params:

* **mask** file mask to search in (i.e. */var/folder1/\*.jpg*)
* **mode** file open mode

Returns a file stream.

Raises an exception if the parameter *pass_errors=false* is set in the macro
config and the file can not be opened.

System functions
================

.. _m_alias:

alias - create object alias
---------------------------

The functions allows to create object alias, e.g. make a short alias for a
long-named function.

.. code-block:: python

    alias(alias_obj, src_obj)

params:

* **alias_obj** alias object
* **src_obj** source object

Returns *True* if alias is set, *False* if not (e.g. src_obj is not found).

Usage example: you have a function *very_long_function* and want to make *f1*
alias for it. All you need is to put in **xc/lm/common.py** the following code:

.. code-block:: python

    alias('f1', 'very_long_function')

The difference between Python code *f1=very_long_function* is that such code
will throw an exception if *very_long_function* is not found, while **alias**
macro function will pass an error and return *False*.

.. _m_sleep:

sleep - pause operations
------------------------

.. code-block:: python

    # alias for python time.sleep
    sleep(seconds.milliseconds)

time - get current UNIX timestamp
---------------------------------

.. code-block:: python

    # alias for python time.time
    time()

mail - send email message
-------------------------

.. code-block:: python

    mail(subject=None, text=None, rcp=None)

params:

* **subject** email subject
* **text** email text
* **rcp** recipient or array of the recipients

The function uses **[mailer]** section of the :ref:`LM PLC
configuration<lm_ini>` to get sender address and list of the recipients (if not
specified).

Returns *True* if the message is sent successfully.

get - HTTP/GET request
----------------------

.. code-block:: python

    # alias for requests.get
    get(uri, args)

See `requests <http://docs.python-requests.org/en/master/>`_ documentation for
more info.

post - HTTP/POST request
------------------------

.. code-block:: python

    # alias for requests.post
    post(uri, args)

See `requests <http://docs.python-requests.org/en/master/>`_ documentation for
more info.

system - execute OS command
---------------------------

.. code-block:: python

    # alias for python os.system
    system(command)


.. _m_cmd:

cmd - execute command script
----------------------------

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
---------------------------------

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
-----------------

Finishes macro execution

.. code-block:: python

    exit(code=0)

params:

* **code** macro exit code (0 - no errors)

Extending macros functionality
==============================

Macros function set can be extended with pre-made or custom :doc:`macro
extensions</lm/ext>`. As soon as extension is loaded, its functions become
available in all macros without a need to restart :doc:`LM PLC</lm/lm>`.
