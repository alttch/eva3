Logic control macros
====================

In :doc:`lm` macros can be triggered on the list of events, third-party
applications or user via :doc:`LM EI<lm_ei>` interface or :doc:`LM API<lm_api>`
functions.

Macro code is located the file written in Python and located in the folder
**xc/lm/** under the name <macro_id>.py, i.e. *test.py* for "test" macro. Macro
id should be unique within the single LM PLC, full id (group/id) - within the
whole installation.

Additionally, each macro is automatically appended with common.py file located
in the same folder enabling to quickly assign common functions to several
macros without using modules.

Macros are compiled into byte-code each time after macros file or common.py
file are changed. Compilation or execution errors can be viewed in the log
files of the controller.

Executing macros
----------------

To execute a macro, use **run** command of :doc:`lm-cmd</cli>` or LM API
:ref:`run<l_run>` function.

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

After the macros code is placed into *xc/lm/<macro_id>.py* file, it should be
appended to the controller using :ref:`create_macro<l_create_macro>` LM API
function or with **lm-cmd**.

After the macros is attached, you may configure it's params using
:ref:`set_macro_prop<l_set_macro_prop>`.

Parameters:

* **id** macros id, can't be modified after the macro is created
* **action_enabled** *true* means macro can be executed (true by default) *
  **action_exec** controller gets the code of the macro from the file
  *<macro_id>.py* by default, use this parameter to assign another file.
* **description** macro description
* **group** macro group (in difference to other objects, macro group can be
  changed after creation)
* **pass_errors** if *true*, in case the function called by macro is completed
  with an exception, the controller ignores this and continue the code
  execution (false by default)

Common principles of macros operation
-------------------------------------

Macros are launched simultaneously: system does not wait for the completion of
the macro and launches its next copy or another macro in parallel. If you want
only one copy of macro to operate at a certain point of tme or to block
execution of the other macros, use macro :ref:`lock<m_lock>` and
:ref:`unlock<m_unlock>` functions.

The system architecture does not provide the possibility to stop macro from
outside, that is why macros should have minimum internal logic and cycles.

All the logic should be implemented in the :doc:`decision-making
matrix<decision_matrix>`. The working cycles should be implemented with
:ref:`logic variables<lvar>` timers.

System macros
-------------

If defined, macro called *system/autoexec* is launched automatically after
controller start. The macro is not always the first one executed, as far as
some initial :doc:`decision-making rules<decision_matrix>` may call assigned
macros, or some events may be handled before. In case macro is launched later
than :ref:`logic variables<lvar>` or other loadable items update their status
(e. g. due to slow connection with :ref:`MQTT server<mqtt_>`) it's recommended
to use :ref:`sleep<m_sleep>` function to do a small delay.

Macros from **system** group are considered as the local system macros and
aren't synchronized to :doc:`SFA</sfa/sfa>`.

Example of *autoexec* macro usage:

.. code-block:: python

    # both cycle timers are expired
    if is_expired('timers/timer1') and is_expired('timers/timer2'):
        # launch the first cycle process
        action('pumps/pump1', on)
        # start the first cycle timer
        reset('timers/timer1')

Macros and security
-------------------

As all Python features are available for macro, including the execution of the
external programs or working with any local files, code of the macros should be
edited only by the system administrator.

If access permissions to the individual macros are configured via API keys, you
should take into account the following: if macro runs other macros via
:ref:`run<m_run>` function, these macros will be executed even if the API key
allows to run only the initial macro.

Macro functions and variables
-----------------------------

Macros can execute any Python functions or use Python modules installed on the
local server. In addition macros have a set of the built-in functions and
variables.

Built-in functions are include for quick access to most frequently used Python
functions as well as :doc:`lm_api` and :doc:`/uc/uc_api`. While calling API
function, item id is always transmitted in full. For calling other macros and
working with logic variables it is possible to use the short ids only.

Macro variables
~~~~~~~~~~~~~~~

Macros have the following built-in variables:

* **on** alias to integer *1*
* **off** alias to integer *0*
* **yes** alias to boolean *True*
* **no** alias to boolean *False*

* **_source** item generated the :doc:`event<decision_matrix>` used by the
  system to call this macro. You may directly access the item and i.e. use it's
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

    if macro arguments/lm_cvars are numbers, they're automatically converted
    into float type


