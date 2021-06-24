Logic macros
************

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

To execute a macro, use **macro run** command of :doc:`eva lm</cli>` or LM API
:ref:`run<lmapi_run>` function.

.. note::

    If you need to execute or use a single macro function, you may do this
    directly, adding "@" symbol to function name, e.g. *@action_toggle*,
    *@start*, etc.

Debugging macros
================

Macro compilation and execution errors are written into the logs of the
controller on DEBUG level, the exceptions are also added to **err** field of
the execution result.

To receive information about errors you may run the following command:

.. code-block:: bash

    eva lm -J run <macro_id> -w 3600 | jq -r .err

Macros configuration
====================

After the macro code is placed into *xc/lm/<macro_id>.py* file, it should be
appended to the controller using :ref:`create_macro<lmapi_create_macro>` LM API
function or with **eva lm**.

After the macro configuration is created, you may view its params using
:ref:`list_macro_props<lmapi_list_macro_props>` and change them with
:ref:`set_macro_prop<lmapi_set_macro_prop>`.

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
  core with *critical(msg, send_event=True)*

Common principles of macros operation
=====================================

Macros are launched simultaneously: system does not wait for the completion of
the macro and launches its next copy or another macro in parallel. If you want
only one copy of macro to operate at the certain point of time or to block
execution of other macros, use macro :ref:`lock<macro_api_lock>` and
:ref:`unlock<macro_api_unlock>` functions.

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
to use :ref:`sleep<macro_api_sleep>` function to do a small delay.

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
controller shutdown. This macro can, for example, gracefully stop cycles and
set/reset required :ref:`logic variables<lvar>`. The macro should end its work
in default controller timeout.

Macros and security
===================

As all Python features are available for macros, including execution of
external programs or working with any local files, the code of macros should be
edited only by system administrator.

If access permissions to individual macros are configured via API keys, you
should take into account the following: if a macro runs other macros using
:ref:`run<macro_api_run>` function, these macros will be executed even if the
API key allows to run only the initial macro.

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
* **args** array list of arguments the macro is being executed with
* **kwargs** dict of keyword arguments the macro is being executed with
* **_0** current macro id (i.e. *'test'*)
* **_00** current macro full id (i.e. *'group1/test'*)
* **_1, _2, ... _9** first 9 arguments the macro is being executed with
* **out** macro may use this variable to output the data which will be set to
  **out** field of the execution result
* **is_shutdown** contains a function which returns *True* if macro caller got
  a core shutdown or :doc:`cycle<cycles>` stop event.
* all :ref:`lm_cvars<lm_cvars>` variables

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

 * **json** `JSON processing <https://docs.python.org/3/library/json.html>`_
 * **os** standard `Python OS functions <https://docs.python.org/3/library/os.html>`_
 * **requests** `HTTP functions <http://docs.python-requests.org/en/master/>`_
 * **sys** `standard Python system functions <https://docs.python.org/3/library/sys.html>`_


.. _macro_api_cat_general:

General functions
=================



.. _macro_api_alias:

alias - create object alias
---------------------------



.. code-block:: python

    alias('rpush', 'roboger_local_push')

Parameters:

* **alias_obj** alias object
* **src_obj** source object

Returns:

True if alias is set. Doesn't raise any exceptions, safe to use in common files


.. _macro_api_cmd:

cmd - execute a remote system command
-------------------------------------

Executes a :ref:`command script<cmd>` on the server where the controller is installed.

.. code-block:: python

    r = cmd('uc/mws1-v1', 'test', wait=5)

Parameters:

* **controller_id** controller id to execute command on
* **command** name of the command script

Optionally:

* **args** string of command arguments, separated by spaces (passed to the script)
* **wait** wait (in seconds) before API call sends a response. This allows to try waiting until command finish
* **timeout** maximum time of command execution. If the command fails to finish within the specified time (in sec), it will be terminated
* **stdin_data** data to be passed to script STDIN

Returns:

Serialized command action object (dict)

.. code-block:: json

    {
        "args": [],
        "cmd": "test",
        "err": "some text to stderr\n",
        "exitcode": 0,
        "out": "test script start\nparam 1:  ( > 0 will generate \"failed\" status)\nparam 2: \nparam 3: \ndelay 3 sec\nscript finish\n",
        "status": "completed",
        "time": {
            "completed": 1553466937.5606368,
            "created": 1553466934.5421243,
            "running": 1553466934.5424464
        },
        "timeout": 5.0
    }

Raises:

* **ResourceNotFound** command script or controller is not found


.. _macro_api_date:

date - date/time
----------------



.. code-block:: python

    r = date()

Returns:

Serialized date/time object (dict)

.. code-block:: json

    {
        "day": 14,
        "hour": 0,
        "minute": 47,
        "month": 5,
        "second": 16,
        "timestamp": 1557787636.680612,
        "weekday": 1,
        "year": 2019
    }


.. _macro_api_decrement_shared:

decrement_shared - decrement value of the shared variable
---------------------------------------------------------

Decrement value of the variable, shared between controller macros. Initial value must be number

.. code-block:: python

    decrement_shared('counter1')

Parameters:

* **name** variable name


.. _macro_api_exit:

exit - finish macro execution
-----------------------------



.. code-block:: python

    exit(1)

Parameters:

* **code** macro exit code (default: 0, no errors)


.. _macro_api_get_directory:

get_directory - get path to EVA ICS directory
---------------------------------------------



Parameters:

* **tp** directory type: eva, runtime, ui, pvt or xc

Raises:

* **LookupError** if directory type is invalid


.. _macro_api_increment_shared:

increment_shared - increment value of the shared variable
---------------------------------------------------------

Increment value of the variable, shared between controller macros. Initial value must be number

.. code-block:: python

    increment_shared('counter1')

Parameters:

* **name** variable name


.. _macro_api_ls:

ls - list files in directory
----------------------------

If recursive is true, the pattern "**" will match any files and zero or more directories and subdirectories.

.. code-block:: python

    r = ls('/opt/i/*.jpg')

Parameters:

* **mask** path and mask (e.g. /opt/data/\*.jpg)
* **recursive** if True, perform a recursive search

Returns:

dict with fields 'name' 'file', 'size' and 'time' { 'c': created, 'm': modified }

.. code-block:: json

    [
        {
            "file": "/opt/i/20170926_004347.jpg",
            "name": "20170926_004347.jpg",
            "size": 6464873,
            "time": {
                "c": 1553460493.280853,
                "m": 1506379536.0
            }
        },
        {
            "file": "/opt/i/20171017_095941.jpg",
            "name": "20171017_095941.jpg",
            "size": 1650389,
            "time": {
                "c": 1553460493.2968528,
                "m": 1510695841.0
            }
        },
        {
            "file": "/opt/i/20171029_194029.jpg",
            "name": "20171029_194029.jpg",
            "size": 3440296,
            "time": {
                "c": 1553460493.324853,
                "m": 1510695762.0
            }
        },
        {
            "file": "/opt/i/20170926_004334.jpg",
            "name": "20170926_004334.jpg",
            "size": 6523001,
            "time": {
                "c": 1553460493.1648533,
                "m": 1506379526.0
            }
        }
    ]


.. _macro_api_mail:

mail - send email message
-------------------------

The function uses *config/common/mailer* :doc:`registry</registry>` key to get
sender address and list of the recipients (if not specified).

.. code-block:: python

    mail(subject='we have a problem', text='sensor 5 is down')

Optionally:

* **subject** email subject
* **text** email text
* **rcp** recipient or array of the recipients

Raises:

* **FunctionFailed** mail is not sent


.. _macro_api_open_newest:

open_newest - open newest file by mask
--------------------------------------



.. code-block:: python

    i = open_newest('/opt/i/*.jpg', 'rb').read()
    print(r)

    None

Parameters:

* **mask** path and mask (e.g. /opt/data/\*.jpg)

Optionally:

* **mode** file open mode (default: 'r')

Returns:

file descriptor

Raises:

* **Exception** exceptions equal to Python "open" function


.. _macro_api_open_oldest:

open_oldest - open oldest file by mask
--------------------------------------



.. code-block:: python

    i = open_oldest('/opt/i/*.jpg', 'rb').read()
    print(r)

    None

Parameters:

* **mask** path and mask (e.g. /opt/data/\*.jpg)

Optionally:

* **mode** file open mode (default: 'r')

Returns:

file descriptor

Raises:

* **Exception** exceptions equal to Python "open" function


.. _macro_api_ping:

ping - ping remote host
-----------------------

Requires fping tool

Parameters:

* **host** host name or IP to ping
* **timeout** ping timeout in milliseconds (default: 1000)
* **count** number of packets to send (default: 1)

Returns:

True if host is alive, False if not


.. _macro_api_run:

run - execute another macro
---------------------------

Execute a macro with the specified arguments.

.. code-block:: python

    r = run('tests/test1', kwargs={'v1': 'test', 'v2': 999}, wait=2)

Parameters:

* **macro** macro id

Optionally:

* **args** macro arguments, array or space separated
* **kwargs** macro keyword arguments, name=value, comma separated or dict
* **wait** wait for the completion for the specified number of seconds
* **uuid** action UUID (will be auto generated if none specified)
* **priority** queue priority (default is 100, lower is better)

Returns:

Serialized macro action object (dict)

.. code-block:: json

    {
        "args": [],
        "err": "",
        "exitcode": 0,
        "finished": true,
        "finished_in": 0.0047829,
        "item_group": "tests",
        "item_id": "test1",
        "item_oid": "lmacro:tests/test1",
        "item_type": "lmacro",
        "kwargs": {
            "v1": "test",
            "v2": 999
        },
        "out": "",
        "priority": 100,
        "status": "completed",
        "time": {
            "completed": 1559869087.3697698,
            "created": 1559869087.364987,
            "pending": 1559869087.3653126,
            "queued": 1559869087.3661342,
            "running": 1559869087.3669574
        },
        "uuid": "fc0e8c8e-9c93-49c4-bb30-e7905fedc33f"
    }

Raises:

* **ResourceNotFound** macro is not found


.. _macro_api_set_shared:

set_shared - set value of the shared variable
---------------------------------------------

Set value of the variable, shared between controller macros

.. code-block:: python

    set_shared('var1', 777)

Parameters:

* **name** variable name

Optionally:

* **value** value to set. If empty, varible is deleted


.. _macro_api_sha256sum:

sha256sum - calculate SHA256 sum
--------------------------------



Parameters:

* **value** value to calculate
* **hexdigest** return binary digest or hex (True, default)

Returns:

sha256 digest


.. _macro_api_shared:

shared - get value of the shared variable
-----------------------------------------

Get value of the variable, shared between controller macros

.. code-block:: python

    r = shared('var1')
    print(r)

    777

Parameters:

* **name** variable name

Optionally:

* **default** value if variable doesn't exist

Returns:

variable value, None (or default) if variable doesn't exist


.. _macro_api_sleep:

sleep - pause operations
------------------------

Unlike standard time.sleep(...), breaks pause when controller shutdown event is received.

.. code-block:: python

    sleep(0.1)

Parameters:

* **t** number of seconds to sleep

Optionally:

* **safe** break on shutdown event (default is True)

Returns:

True if sleep is finished, False if shutdown event is received


.. _macro_api_system:

system - execute the command in a subshell
------------------------------------------



.. code-block:: python

    r = system('touch /tmp/1.dat')
    print(r)

    0

Returns:

shell exit code (0 - no error)


.. _macro_api_time:

time - current time in seconds since Epoch
------------------------------------------

Return the current time in seconds since the Epoch. Fractions of a second may be present if the system clock provides them.

.. code-block:: python

    r = time()
    print(r)

    1553461581.549374



.. _macro_api_cat_item:

Item functions
==============



.. _macro_api_history:

history - get item state history
--------------------------------

To use this function, DB or TSDB notifier in LM PLC must be present. (notifier can share DB with SFA in read/only mode).

.. code-block:: python

    r = history('lvar:tests/test1', t_start='2019-03-24')

Parameters:

* **item_id** item ID, or multiple IDs (list or comma separated)

Optionally:

* **t_start** time frame start, ISO or Unix timestamp
* **t_end** time frame end, optional (default: current time), ISO or Unix timestamp
* **limit** limit history records
* **prop** item property ('status' or 'value'
* **time_format** time format, 'iso' or 'raw' (default) for timestamp
* **fill** fill frame with the specified interval (e.g. *1T* - 1 minute, *2H* - 2 hours etc.), optional. If specified, t_start is required
* **fmt** output format, 'list' (default) or 'dict'
* **db** :doc:`notifier</notifiers>` ID which keeps history for the specified item(s) (default: **db_1**)

Returns:

list of dicts or dict of lists

.. code-block:: json

    {
        "status": [
            1,
            1,
            1,
            1
        ],
        "t": [
            1553461864.9564857,
            1553461878.8139935,
            1553461883.1168087,
            1553461887.6495461
        ],
        "value": [
            0.0,
            0.0,
            1.0,
            1.0
        ]
    }


.. _macro_api_lvar_status:

lvar_status - get lvar status
-----------------------------



.. code-block:: python

    r = lvar_status('tests/test1')
    print(r)

    1

Parameters:

* **lvar_id** lvar id

Returns:

lvar status (integer)

Raises:

* **ResourceNotFound** lvar is not found


.. _macro_api_lvar_value:

lvar_value - get lvar value
---------------------------



.. code-block:: python

    r = lvar_value('tests/test1')
    print(r)

    1.0

Parameters:

* **lvar_id** lvar id

Returns:

lvar value


.. _macro_api_sensor_status:

sensor_status - get sensor status
---------------------------------



.. code-block:: python

    r = sensor_status('env/temp_test')
    print(r)

    1

Parameters:

* **sensor_id** sensor id

Returns:

sensor status (integer)

Raises:

* **ResourceNotFound** sensor is not found


.. _macro_api_sensor_value:

sensor_value - get sensor value
-------------------------------



.. code-block:: python

    r = sensor_value('env/temp_test')
    print(r)

    191.0

Parameters:

* **sensor_id** sensor id

Optionally:

* **default** value if null (default is empty string)

Returns:

sensor value

Raises:

* **ResourceNotFound** sensor is not found


.. _macro_api_state:

state - get item state
----------------------



.. code-block:: python

    r = state('sensor:env/temp1')

Parameters:

* **item_id** item id (oid required)

Returns:

item status/value dict

.. code-block:: json

    {
        "status": 1,
        "value": 55.0
    }

Raises:

* **ResourceNotFound** item is not found


.. _macro_api_status:

status - get item status
------------------------



.. code-block:: python

    r = status('unit:tests/unit1')
    print(r)

    0

Parameters:

* **item_id** item id (oid required)

Returns:

item status (integer)

Raises:

* **ResourceNotFound** item is not found


.. _macro_api_unit_nstatus:

unit_nstatus - get unit nstatus
-------------------------------

nstatus is the status which is set to unit after the current running action is completed.

the function may be called with an alias "nstatus(...)"

.. code-block:: python

    r = unit_nstatus('tests/unit1')
    print(r)

    0

Parameters:

* **unit_id** unit id

Returns:

unit nstatus (integer)

Raises:

* **ResourceNotFound** unit is not found


.. _macro_api_unit_nvalue:

unit_nvalue - get unit nvalue
-----------------------------

nvalue is the value which is set to unit after the current running action is completed.

the function may be called with an alias "nvalue(...)"

.. code-block:: python

    r = unit_nvalue('tests/unit1')
    print(r)



Parameters:

* **unit_id** unit id

Returns:

unit nvalue

Raises:

* **ResourceNotFound** unit is not found


.. _macro_api_unit_status:

unit_status - get unit status
-----------------------------



.. code-block:: python

    r = unit_status('tests/unit1')
    print(r)

    0

Parameters:

* **unit_id** unit id

Returns:

unit status (integer)

Raises:

* **ResourceNotFound** unit is not found


.. _macro_api_unit_value:

unit_value - get unit value
---------------------------



.. code-block:: python

    r = unit_value('tests/unit1')
    print(r)



Parameters:

* **unit_id** unit id

Optionally:

* **default** value if null (default is empty string)

Returns:

unit value

Raises:

* **ResourceNotFound** unit is not found


.. _macro_api_value:

value - get item value
----------------------



.. code-block:: python

    r = value('sensor:env/temp_test')
    print(r)

    191.0

Parameters:

* **item_id** item id (oid required)

Optionally:

* **default** value if null (default is empty string)

Returns:

item value

Raises:

* **ResourceNotFound** item is not found



.. _macro_api_cat_lvar:

LVar functions
==============



.. _macro_api_clear:

clear - reset lvar value
------------------------

Set lvar value to 0 or stop timer lvar (set timer status to 0)

.. code-block:: python

    clear('tests/test1')

Parameters:

* **lvar_id** lvar id

Raises:

* **FunctionFailed** lvar value set error
* **ResourceNotFound** lvar is not found


.. _macro_api_decrement:

decrement - decrement lvar value
--------------------------------

Decrement value of lvar. Initial value should be number

.. code-block:: python

    decrement('tests/test1')

Parameters:

* **lvar_id** lvar id

Raises:

* **FunctionFailed** lvar value decrement error
* **ResourceNotFound** lvar is not found


.. _macro_api_expires:

expires - set lvar expiration time
----------------------------------



.. code-block:: python

    expires('timers/timer1', 30)

Parameters:

* **lvar_id** lvar id

Optionally:

* **etime** time (in seconds), default is 0 (never expires)

Raises:

* **FunctionFailed** lvar expiration set error
* **ResourceNotFound** lvar is not found


.. _macro_api_increment:

increment - increment lvar value
--------------------------------

Increment value of lvar. Initial value should be number

.. code-block:: python

    increment('tests/test1')

Parameters:

* **lvar_id** lvar id

Raises:

* **FunctionFailed** lvar value increment error
* **ResourceNotFound** lvar is not found


.. _macro_api_is_expired:

is_expired - is lvar (timer) expired
------------------------------------



.. code-block:: python

    r = is_expired('nogroup/timer1')
    print(r)

    True

Parameters:

* **lvar_id** lvar id

Returns:

True, if timer has expired

Raises:

* **ResourceNotFound** lvar is not found


.. _macro_api_reset:

reset - reset lvar value
------------------------

Set lvar value to 1 or start lvar timer

.. code-block:: python

    reset('tests/test1')

Parameters:

* **lvar_id** lvar id

Raises:

* **FunctionFailed** lvar value set error
* **ResourceNotFound** lvar is not found


.. _macro_api_set:

set - set lvar value
--------------------



.. code-block:: python

    set('tests/test1', value=1)

Parameters:

* **lvar_id** lvar id

Optionally:

* **value** lvar value (if not specified, lvar is set to null)

Raises:

* **FunctionFailed** lvar value set error
* **ResourceNotFound** lvar is not found


.. _macro_api_toggle:

toggle - toggle lvar value
--------------------------

Change lvar value to opposite boolean (0->1, 1->0)

.. code-block:: python

    toggle('tests/test1')

Parameters:

* **lvar_id** lvar id

Raises:

* **FunctionFailed** lvar value set error
* **ResourceNotFound** lvar is not found



.. _macro_api_cat_unit:

Unit control
============



.. _macro_api_action:

action - unit control action
----------------------------

The call is considered successful when action is put into the action queue of selected unit.

.. code-block:: python

    r = action('tests/unit1', status=1, wait=5)

Parameters:

* **unit_id** unit id
* **status** desired unit status

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
        "finished": true,
        "finished_in": 0.0149484,
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
            "completed": 1559869105.9634602,
            "created": 1559869105.9485118,
            "pending": 1559869105.9487257,
            "queued": 1559869105.9491074,
            "running": 1559869105.949467
        },
        "uuid": "4bce26a6-7203-4a3c-a123-14c144dcc613"
    }

Raises:

* **FunctionFailed** action is "dead"
* **ResourceNotFound** unit is not found


.. _macro_api_action_toggle:

action_toggle - toggle unit status
----------------------------------

Create unit control action to toggle its status (1->0, 0->1). if using OID, you can also call "toggle(..)" with the same effect.

.. code-block:: python

    r = action_toggle('tests/unit1', wait=5)

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
        "nvalue": "",
        "out": "",
        "priority": 100,
        "status": "completed",
        "time": {
            "completed": 1553465690.1327171,
            "created": 1553465690.1081843,
            "pending": 1553465690.1084123,
            "queued": 1553465690.1089923,
            "running": 1553465690.1094682
        },
        "uuid": "0982213a-6c8f-4df3-8581-d1281d0f41dc"
    }

Raises:

* **FunctionFailed** action is "dead"
* **ResourceNotFound** unit is not found


.. _macro_api_is_busy:

is_busy - is unit busy
----------------------



.. code-block:: python

    r = is_busy('tests/unit1')
    print(r)

    False

Parameters:

* **unit_id** unit id

Returns:

True, if unit is busy (action is executed)

Raises:

* **ResourceNotFound** unit is not found


.. _macro_api_kill:

kill - kill unit actions
------------------------

Apart from canceling all queued commands, this function also terminates the current running action.

.. code-block:: python

    kill('tests/unit1')

Parameters:

* **unit_id** unit id

Raises:

* **ResourceNotFound** unit is not found


.. _macro_api_q_clean:

q_clean - clean action queue of unit
------------------------------------

Cancels all queued actions, keeps the current action running.

.. code-block:: python

    q_clean('tests/unit1')

Parameters:

* **unit_id** unit id

Raises:

* **ResourceNotFound** unit is not found


.. _macro_api_result:

result - get action status
--------------------------

Checks the result of the action by its UUID or returns the actions for the specified unit.

.. code-block:: python

    r = result(unit_id='tests/unit1')

Parameters:

* **unit_id** unit id or
* **uuid** action uuid

Optionally:

* **group** filter by unit group
* **status** filter by action status: Q for queued, R for running, F for finished

Returns:

list or single serialized action object

.. code-block:: json

    [
        {
            "err": "",
            "exitcode": 0,
            "finished": true,
            "finished_in": 0.0147429,
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
                "completed": 1559869099.8924437,
                "created": 1559869099.8777008,
                "pending": 1559869099.8778677,
                "queued": 1559869099.8782423,
                "running": 1559869099.8786528
            },
            "uuid": "d5b82c8c-9a95-482a-9063-e3048addc741"
        },
        {
            "err": "",
            "exitcode": 0,
            "finished": true,
            "finished_in": 0.0149484,
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
                "completed": 1559869105.9634602,
                "created": 1559869105.9485118,
                "pending": 1559869105.9487257,
                "queued": 1559869105.9491074,
                "running": 1559869105.949467
            },
            "uuid": "4bce26a6-7203-4a3c-a123-14c144dcc613"
        }
    ]

Raises:

* **ResourceNotFound** unit or action is not found


.. _macro_api_start:

start - start unit
------------------

Create unit control action to set its status to 1

.. code-block:: python

    r = start('tests/unit1', wait=5)

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
        "finished": true,
        "finished_in": 0.0179181,
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
            "completed": 1559869092.8558156,
            "created": 1559869092.8378975,
            "pending": 1559869092.838309,
            "queued": 1559869092.8390505,
            "running": 1559869092.8402033
        },
        "uuid": "bf74b19c-2af1-40f6-9ec6-5f74bb572558"
    }

Raises:

* **FunctionFailed** action is "dead"
* **ResourceNotFound** unit is not found


.. _macro_api_stop:

stop - stop unit
----------------

Create unit control action to set its status to 0

.. code-block:: python

    r = stop('tests/unit1', wait=5)

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
        "finished": true,
        "finished_in": 0.0147429,
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
            "completed": 1559869099.8924437,
            "created": 1559869099.8777008,
            "pending": 1559869099.8778677,
            "queued": 1559869099.8782423,
            "running": 1559869099.8786528
        },
        "uuid": "d5b82c8c-9a95-482a-9063-e3048addc741"
    }

Raises:

* **FunctionFailed** action is "dead"
* **ResourceNotFound** unit is not found


.. _macro_api_terminate:

terminate - terminate action execution
--------------------------------------

Terminates or cancel the action if it is still queued

.. code-block:: python

    try:
    terminate(unit_id='tests/unit1')
    except ResourceNotFound:
    print('no action running')

Parameters:

* **unit_id** action uuid or
* **uuid** unit id

Raises:

* **ResourceNotFound** if unit/action is not found or action is already finished



.. _macro_api_cat_rule:

Rule management
===============



.. _macro_api_set_rule_prop:

set_rule_prop - set rule prop
-----------------------------



.. code-block:: python

    set_rule_prop('28af95b2-e087-47b3-a6cd-15fe21d06c4a', 'condition', 'x < 5')

Parameters:

* **rule_id** rule id (uuid)
* **prop** property to set
* **value** value to set

Optionally:

* **save** save rule config after the operation

Raises:

* **ResourceNotFound** rule is not found



.. _macro_api_cat_job:

Scheduled job management
========================



.. _macro_api_set_job_prop:

set_job_prop - set job prop
---------------------------



.. code-block:: python

    set_job_prop('6970e296-5cb4-4448-9f2a-1ab2a14ed7f1', 'enabled', True)

Parameters:

* **job_id** job id (uuid)
* **prop** property to set
* **value** value to set

Optionally:

* **save** save job config after the operation

Raises:

* **ResourceNotFound** job is not found



.. _macro_api_cat_device:

Devices
=======



.. _macro_api_deploy_device:

deploy_device - deploy device items from template
-------------------------------------------------

Deploys the :ref:`device<device>` from the specified template.

.. code-block:: python

    deploy_device('uc/mws1-v1', 'device1', cfg={ 'ID': 5 })

Parameters:

* **controller_id** controller id to deploy device on
* **device_tpl** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Optionally:

* **cfg** device config (*var=value*, comma separated or dict)
* **save** save items configuration on disk immediately after operation

Raises:

* **ResourceNotFound** device template or controller is not found
* **FunctionFailed** device deploy error


.. _macro_api_undeploy_device:

undeploy_device - undeploy device items config from template
------------------------------------------------------------



.. code-block:: python

    undeploy_device('uc/mws1-v1', 'device1', cfg={ 'ID': 5 })

Parameters:

* **controller_id** controller id to deploy device on
* **device_tpl** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Optionally:

* **cfg** device config (*var=value*, comma separated or dict)

Raises:

* **ResourceNotFound** device template or controller is not found


.. _macro_api_update_device:

update_device - update device items config from template
--------------------------------------------------------



.. code-block:: python

    update_device('uc/mws1-v1', 'device1', cfg={ 'ID': 5 })

Parameters:

* **controller_id** controller id to deploy device on
* **device_tpl** device template (*runtime/tpl/<TEMPLATE>.yml|yaml|json*, without extension)

Optionally:

* **cfg** device config (*var=value*, comma separated or dict)
* **save** save items configuration on disk immediately after operation

Raises:

* **ResourceNotFound** device template or controller is not found
* **FunctionFailed** device update error



.. _macro_api_cat_cycle:

Logic cycles
============



.. _macro_api_get_cycle_info:

get_cycle_info - get cycle information
--------------------------------------



.. code-block:: python

    r = get_cycle_info('tests/cycle1')

Parameters:

* **cycle_id** cycle id

Returns:

dict with cycle information

.. code-block:: json

    {
        "description": "",
        "full_id": "tests/cycle1",
        "group": "tests",
        "ict": 20,
        "id": "cycle1",
        "interval": 0.01,
        "iterations": 0,
        "macro": "tests/test",
        "oid": "lcycle:tests/cycle1",
        "on_error": null,
        "status": 0,
        "type": "lcycle"
    }

Raises:

* **ResourceNotFound** cycle is not found


.. _macro_api_is_cycle_running:

is_cycle_running - get cycle running status
-------------------------------------------



.. code-block:: python

    r = is_cycle_running('tests/cycle1')
    print(r)

    True

Parameters:

* **cycle_id** cycle id

Returns:

True if cycle is runing

Raises:

* **ResourceNotFound** cycle is not found


.. _macro_api_list_cycle_props:

list_cycle_props - list cycle props
-----------------------------------



.. code-block:: python

    r = list_cycle_props('tests/cycle1')

Parameters:

* **cycle_id** cycle id

Returns:

dict with cycle props

.. code-block:: json

    {
        "autostart": false,
        "description": "",
        "ict": 20,
        "interval": 0.01,
        "macro": "tests/test",
        "on_error": null
    }

Raises:

* **ResourceNotFound** cycle is not found


.. _macro_api_reset_cycle_stats:

reset_cycle_stats - reset cycle stats
-------------------------------------



.. code-block:: python

    reset_cycle_stats('tests/cycle1')

Parameters:

* **cycle_id** cycle id

Raises:

* **ResourceNotFound** cycle is not found


.. _macro_api_set_cycle_prop:

set_cycle_prop - set cycle prop
-------------------------------



.. code-block:: python

    set_cycle_prop('tests/cycle1', 'ict', 20)

Parameters:

* **cycle_id** cycle id
* **prop** property to set
* **value** value to set

Optionally:

* **save** save cycle config after the operation

Raises:

* **ResourceNotFound** cycle is not found


.. _macro_api_start_cycle:

start_cycle - start cycle
-------------------------



.. code-block:: python

    start_cycle('tests/cycle1')

Parameters:

* **cycle_id** cycle id

Raises:

* **ResourceNotFound** cycle is not found


.. _macro_api_stop_cycle:

stop_cycle - stop cycle
-----------------------



.. code-block:: python

    stop_cycle('tests/cycle1', wait=True)

Parameters:

* **cycle_id** cycle id

Optionally:

* **wait** wait for cycle stop (default is False)

Raises:

* **ResourceNotFound** cycle is not found



.. _macro_api_cat_lock:

Locking functions
=================



.. _macro_api_lock:

lock - acquire lock
-------------------



.. code-block:: python

    lock('lock1', expires=1)

Parameters:

* **lock_id** lock id

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



.. _macro_api_cat_log:

Logging
=======



.. _macro_api_debug:

debug - put debug message to log file
-------------------------------------



.. code-block:: python

    debug('this is a test debug message')

Parameters:

* **msg** message text


.. _macro_api_info:

info - put info message to log file
-----------------------------------

Additionally, print() function is alias to info()

.. code-block:: python

    info('this is a test debug message')

Parameters:

* **msg** message text


.. _macro_api_warning:

warning - put warning message to log file
-----------------------------------------



.. code-block:: python

    info('this is a test debug message')

Parameters:

* **msg** message text


.. _macro_api_error:

error - put error message to log file
-------------------------------------



.. code-block:: python

    error('this is a test debug message')

Parameters:

* **msg** message text


.. _macro_api_critical:

critical - put critical message to log file
-------------------------------------------



.. code-block:: python

    critical('this is a test debug message')

Parameters:

* **msg** message text

Optionally:

* **send_event** if True, critical event to core is sent (requires send_critical=true in macro props)


