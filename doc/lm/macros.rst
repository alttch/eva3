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
* **send_critical** if *true*, allows to send critical events to controller
  with *critical(msg, send_event=True)*

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

On startup
----------

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

On shutdown
-----------

If defined, macro named **system/shutdown** is launched automatically at the
controller startup. This macro can, for example, gracefully stop cycles and
set/reset required :ref:`logic variables<lvar>`. The macro should end its work
in default controller timeout.

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
* **_polldelay** controller poll delay
* **_timeout** controller default timeout
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


Extending macros functionality
==============================

Macros function set can be extended with pre-made or custom :doc:`macro
extensions</lm/ext>`. As soon as extension is loaded, its functions become
available in all macros without a need to restart :doc:`LM PLC</lm/lm>`.

Also, macro can import any local Python module. The following modules are
pre-imported:

 * **json** JSON processing
 * **os** standard Python OS functions
 * **requests** HTTP functions
 * **sys** standard Python system functions


.. _macro_api_cat_general:

General functions
=================



.. _macro_api_set_shared:

set_shared - set value of the shared variable
---------------------------------------------

Set value of the variable, shared between node macros

.. code-block:: python

    set_shared('var1', 777)

Parameters:

* **name** variable name

Optionally:

* **value** value to set. If empty, varible is deleted


.. _macro_api_shared:

shared - get value of the shared variable
-----------------------------------------

Get value of the variable, shared between node macros

.. code-block:: python

    result = shared('var1')
    print(result)

    777

Parameters:

* **name** variable name

Optionally:

* **default** value if variable doesn't exist

Returns:

variable value, None (or default) if variable doesn't exist



.. _macro_api_cat_lock:

Locking functions
=================



.. _macro_api_lock:

lock - acquire lock
-------------------



.. code-block:: python

    lock('lock1', expires=1)

Parameters:

* **l** lock id

Optionally:

* **timeout** max timeout to wait
* **expires** time after which token is automatically unlocked (if absent, token may be unlocked only via unlock function)

Returns:

True if lock is acquired

Raises:

* **FunctionFailed** function failed to acquire lock


.. _macro_api_unlock:

unlock - release lock
---------------------

Releases the previously acquired lock.

.. code-block:: python

    unlock('lock1')

Parameters:

* **l** lock id

Returns:

True if lock is released

Raises:

* **ResourceNotFound** lock is not found
* **FunctionFailed** function failed to release lock



.. _macro_api_cat_unit:

Unit control
============



.. _macro_api_is_busy:

is_busy - is unit busy
----------------------



.. code-block:: python

    result = is_busy('tests/unit1')
    print(result)

    False

Parameters:

* **unit_id** unit id

Returns:

True, if unit is busy (action is executed)

Raises:

* **ResourceNotFound** unit is not found


.. _macro_api_start:

start - start unit
------------------

Create unit control action to set its status to 1

.. code-block:: python

    result = start('tests/unit1', wait=5)

Parameters:

* **unit_id** unit id

Optionally:

* **value** desired unit value
* **wait** wait for the completion for the specified number of seconds
* **uuid** action UUID (will be auto generated if none specified)
* **priority** queue priority (default is 100, lower is better)

Returns:

Serialized action object (dict)

.. code-block:: json

    {
        "err": "",
        "exitcode": 0,
        "item_group": "tests",
        "item_id": "unit1",
        "item_oid": "unit:tests/unit1",
        "item_type": "unit",
        "nstatus": 1,
        "nvalue": null,
        "out": "",
        "priority": 100,
        "status": "completed",
        "time": {
            "completed": 1553444253.1421173,
            "created": 1553444253.1185853,
            "pending": 1553444253.1187418,
            "queued": 1553444253.1192524,
            "running": 1553444253.1196089
        },
        "uuid": "ee9b149d-5591-4d9c-aa97-b46146d31332"
    }

Raises:

* **FunctionFailed** action is "dead"
* **ResourceNotFound** unit is not found


.. _macro_api_stop:

stop - stop unit
----------------

Create unit control action to set its status to 0

.. code-block:: python

    result = stop('tests/unit1', wait=5)

Parameters:

* **unit_id** unit id

Optionally:

* **value** desired unit value
* **wait** wait for the completion for the specified number of seconds
* **uuid** action UUID (will be auto generated if none specified)
* **priority** queue priority (default is 100, lower is better)

Returns:

Serialized action object (dict)

.. code-block:: json

    {
        "err": "",
        "exitcode": 0,
        "item_group": "tests",
        "item_id": "unit1",
        "item_oid": "unit:tests/unit1",
        "item_type": "unit",
        "nstatus": 0,
        "nvalue": null,
        "out": "",
        "priority": 100,
        "status": "completed",
        "time": {
            "completed": 1553444253.185795,
            "created": 1553444253.1679392,
            "pending": 1553444253.168088,
            "queued": 1553444253.1684065,
            "running": 1553444253.1688204
        },
        "uuid": "10f717e6-cfe6-4a19-97c0-483c7399ad68"
    }

Raises:

* **FunctionFailed** action is "dead"
* **ResourceNotFound** unit is not found


