Decision-making matrix
**********************

Decision-making matrix is a set of rules and conditions under that :doc:`lm`
runs the specified :doc:`macros<macros>` when certain events occur.

To manage the decision rules you may use **eva lm** (*lm-cmd*) :doc:`console
applications</cli>`, :doc:`lm_api` functions or an appropriate :doc:`lm_ei`
interface section.

Rule configuration is stored in **runtime/lm_dmatrix_rule.d/** folder.

Event analysis algorithms
=========================

Event means any change of the :doc:`item</items>` state. The events are
analyzed and processed in the following way:

* A specific ID is assigned to each event by which you can monitor its
  processing in the logs.

* The system takes the list of all rules sorted by their priority (the lower
  the value, the higher the priority) and description.


* Each rule is analyzed separately, in the order of priority

* Firstly, it's checked whether the rule corresponds to the type, group, ID and
  property of the item that sent the event

* Then, the system is verifying whether the current item state matches the rule
  conditions and the previous one is out of its range

    * For example, there is a temperature sensor; the condition *25 <= x <= 28*
      is specified in the rule; it will match only once - as soon as the
      transmitted temperature reaches 25-28 degrees. The rule will match again
      if the temperature exceeds this range and returns back.
    * When the controller is just started, the previous state is unknown or
      usually outdated. In this case, the system acts according to the
      configuration property of the rule **for_initial**: if it's set to
      *skip*, the rule is ignored, if *only* or *any*, it's verified and the
      rule matches if the current state matches the range.
    * If **for_initial** is set to *only* in the rule configuration, the rule
      is being checked only once, after the controller is started and the
      initial states of the items are received.
    * :ref:`Logic variables<lvar>` always have an initial value stored in the
      local base, that's why **for_initial** should always be any for them to
      let the rules work correctly, unless you really know what you do.
    * If the rule matches, a :doc:`macro<macros>` (if specified) with the
      specified arguments is executed.
    * If chillout_time > 0 in the configuration, the rule is ignored after the
      match for the specified time. If rule matched during chill-out, macro is
      executed once, after chill-out period ends.

Rule creation
=============

Rules can be created with either LM API :ref:`create_rule<lmapi_create_rule>`
function or with :doc:`EVA shell</cli>`.

To configure rule you may specify condition and action, or you may set rule
parameters one-by-one after the rule is created.

To specify condition and action during rule creation, use the following format.
Note that controller doesn't check is condition item and/or macro exists on the
moment of rule creation:

.. code:: bash

    rule create if <condition> [then <action>]

Example, start unit *unit:ventilation/v1* (call *start* macro function) if
value of *sensor:env/temp* is more than 25:

.. code:: bash

    rule create if sensor:env/temp.value > 25 then @start('unit:ventilation/v1')

Another example. Run macro *macro1* if value of lvar *lvar:tests/lvar1* is more
than 25 but less than 35:

.. code:: bash

    rule create if 35 > lvar:tests/lvar1.value > 25 then macro1()

Check only 3rd bit of value:

.. code:: bash

    rule create if sensor:env/plc_state.b3 == 1 then macro1()

.. note::

    New rule is always created as "disabled" and you must enable it with "rule
    enable" CLI command or call LM API function
    :ref:`set_rule_prop<lmapi_set_rule_prop>`, setting *enabled=True*.

Rule configuration
==================

Unmodifiable rule parameters:

* **id** rule id, always generated automatically when it is created
* **chillout_ends_in** a virtual parameter specifying for how long (in seconds)
  the rule is ignored, if **chillout_time** is set

Modifiable Parameters:

* **break_after_exec** if *True* and the rule matches, further rules for the
  event are ignored

* **chillout_time** the rule is ignored for a specified time (in seconds)
  after match

* **condition** "virtual" parameter which allows get/set rule condition in the
  readable format (e.g. *25 < x <= 28*)

* **description** rule description

* **enabled** if *True*, rule is enabled (new rules are disabled by default)

* **for_initial** can be *skip*, *only* or *any* (default is *skip*). Indicates
  the rule processing algorithm when the server is started and the initial item
  states are received

* **for_item_group** the rule matches only for a specific group of items (# or
  null - for all groups)

* **for_item_id** the rule matches only for a specific item (# or null - for
  all items), may contain the mask \*id, id\* or \*id\*, i.e. *\*.temperature*

* **for_item_type** the rule matches only for a specific type of items (# or
  null - for all types)

* **for_oid** "virtual" parameter which allows get/set rule condition in the
  readable format (e.g. sensor:group1/#.value)

* **for_prop** the state property of the item (**status** or **value**) the
  rule is checking. For :ref:`unit<unit>` state, **nstatus** and **nvalue**
  properties may be additionally used.

* **for_prop_bit** if set to a number (0-X), only state Xth bit is compared.
  Obviously, the compassion condition should be set either == 0 or == 1.

* **in_range_max** matches when *x < value*

* **in_range_max_eq** matches when *x <= value* (in_range_max should be
  specified)

* **in_range_min** matches when *x > value*

* **in_range_min_eq** matches when *x >= value* (in_range_min should be
  specified)

* **macro** :doc:`macro<macros>` that is executed when the rule conditions
  match

* **macro_args** arguments the macro is executed with

* **macro_kwargs** keyword arguments the macro is executed with

* **priority** the rule priority (integer; the lower the value, the higher the
  priority, 100 by default)

Tips for rule configuration
===========================

* to set "x == value" condition via `lm_api`: if the value is numeric, use
  "value <= x <= value". If the value is string, you may set only
  **in_range_min_eq**

* if you set a field **for_expire** (with any value, i.e. *Y*) in a rule change
  request, the system automatically sets the rule to *for_prop = status, x <=
  -1*, which means the rule match when the item state is expired. This is
  useful to configure the rule to check for the :ref:`lvar<lvar>` timers
  expiration as well as checking for :ref:`units<unit>` and
  :ref:`sensors<sensor>` error states

* if you set a field **for_set** (with any value, i.e.  *Y*) in a rule change
  request, the system automatically sets the rule to *for_prop = status, x ==
  1*, which means the rule match when the item state is set. This is useful to
  configure the rule to check for the :ref:`lvar<lvar>` timers reset as well as
  working with a logical flags

* if the rule has no **in_range_min** and **in_range_max conditions**, it will
  match each time when the item changes its status (for_prop == status) or
  value (for_prop == value)

If rule option **for_initial** is set to *any* or *only*, it is possible to
cache previous item state to prevent false rule triggering. This may cause
additional system overload.

To enable state cache, set "plc/cache-remote-state" field in *config/lm/main*
:doc:`registry</registry>` key to desired cache time-to-live in seconds (e.g.
604800 = time-to-live 1 week) and restart the controller.

Or use "feature" command:

.. code:: bash

    eva feature setup lm_state_cache ttl=604800
