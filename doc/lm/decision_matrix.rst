Decision-making matrix
======================

Decision-making matrix is a set of rules and conditions under which :doc:`lm`
runs the specified :doc:`macros<macros>` when certain events occur.

To change the decision rules you may use **lm-rules**, **lm-cmd** :doc:`console
applications</cli>`, :doc:`lm_api` functions or an appropriate :doc:`lm_ei`
interface section.

Rule configuration is stored in **runtime/lm_dmatrix_rule.d/** folder.

Event analysis algorithms
-------------------------

Event means any change of the :doc:`item</items>` state. The events are
analyzed and processed in the following way:

* Each event is assigned a specific ID by which you can monitor its processing
  in the log file.

* The system takes the list of all rules sorted by their priority (the lower
  the value, the higher the priority) and description.


* Each rule is analyzed separately, in the order of priority

* Firstly, it's checked whether the rule corresponds to the type, group, ID and
  property of the item that sent the event

* Then, the system is verifying whether the current item state matches the rule
  conditions and the previous one is out of its range

    * For example, there is a temperature sensor; the condition *25 <= x <= 28*
      is specified in the rule; the will match only once - as soon as the
      transmitted temperature reaches 25-28 degrees. The rule will match again
      if the temperature exceeds this range and returns back.
    * When the contoller is just started, the previous state is unknown or
      usually outdated. In this case, the system acts according to the
      configuration property of the rule **for_initial**: if it's set to
      *skip*, the rule is ignored, if *only* or *any*, it's verified and the
      rule matches if the current state match the range.
    * If **for_initial** is set to *only* in the rule configuration, the rule
      is being checked only once, after the contoller is started and received
      the initial states of the items.
    * :ref:`Logic variables<lvar>` always have an initial value stored in the
      local base, that's why **for_initial** should always be any for them to
      let the rules work correctly, unless you really know what yo do.
    * If the rule matches, a :doc:`macro<macros>` (if specified) with the
      specified arguments is executed.
    * If chillout_time > 0 in the configuration, the rule is ignored after the
      match for the specified time.

Rule configuration
------------------

Unmodifiable rule parameters:

* **id** rule id, always generated automatically when it is created
* **chillout_ends_in** a virtual parameter specifying for how long (in seconds)
  the rule is ignored, if **chillout_time** is set
* **condition** a virtual parameter displaying a rule condition in the readable
  format (i.e. *25 < x <= 28*)

Modifiable Parameters:

* **break_after_exec** if *True* and the rule matches, further rules for the
  event are ignored

* **chillout_time** the rule is ignored for a specified time (in seconds)
  after match

* **description** rule description

* **enabled** if *True*, rule is enabled (new rules are disabled by default)

* **for_initial** can be *skip*, *only* or *any* (default is *any*). Indicates
  the rule processing algorithm when the server is started and the initial item
  states are received

* **for_item_group** the rule matches only for a specific group of items ((# or null - for all groups)

* **for_item_id** the rule matches only for a specific item (# or null - for
  all items), may contain the mask \*id, id\* or \*id\*, i.e. *\*.temperature*

* **for_prop** the status property of the item (status or value) the rule is checking

* **in_range_max** matches when *x < value*

* **in_range_max_eq** matches when *x <= value* (in_range_max should be specified)

* **in_range_min** matches when *x > value*

* **in_range_min_eq** matches when *x >= value* (in_range_min should be specified)

* **macro** :doc:`macro<macros>` that's being executed when the rule conditions match

* **macro_args** arguments the macro is executed with

* **priority** the rule priority (integer; the lower the value, the higher the
  priority, 100 by default)

Tips for rule configuration
---------------------------

* to set "x == value" condition via `lm_api`: if the value is numeric, use
  "value <= x <= value". If the value is string, you may set only
  **in_range_min_eq**

* if you set in a rule change request a field **for_expire** (with any value,
  i.e. *Y*), the system automatically sets the rule to *for_prop = status, x <=
  -1*, which means the rule match when the item state is expired. This is
  useful to configure the rule to check for the :ref:`lvar<lvar>` timers
  expiration as well as checking for :ref:`units<unit>` and
  :ref:`sensors<sensor>` error states

* if you set in a rule change request a field **for_set** (with any value, i.e.
  *Y*), the system automatically sets the rule to *for_prop = status, x ==
  1*, which means the rule match when the item state is being set. This is
  useful to configure the rule to check for the :ref:`lvar<lvar>` timers
  reset as well as working with a logical flags

* to delete **in_range_min** and **in_range_max** conditions, use null or none
  in **lm-rules** or blank value in LM API
  :ref:`set_rule_prop<lm_set_rule_prop>`

* if the rule has no **in_range_min** and **in_range_max conditions**, it will
  match each time when the item changes its status (for_prop == status) or
  value (for_prop == value)
