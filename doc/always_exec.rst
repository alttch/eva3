Always exec
***********

Any automation project more complex than a simple relay request features
interfaces and subsystems that independently store the :ref:`unit<unit>` states
and keep them in sync with the real hardware equipment. But sometimes
synchronization is either impossible or failed; occasionally the state updating
is not specified in the configuration at all. In some cases, we may not even
know whether the relay went off or not. A typical reason is unreliability of
the relay and its failure to return the current status.

In this case, there is a "foolproof": the :ref:`action<ucapi_action>` which is
always executed, even if the unit state is the same as requested and is not
supposed to be changed.

It is possible in the following cases:

* If it's a simple electrical circuit without any inner logic in the
  :doc:`script<item_scripts>`: for example, a lamp or an outlet. If the lamp
  has already been turned on, nothing will change if the relay will be switched
  on - it may itself discard such a command. But both us and our system will be
  sure it's really on.
  
It is not recommended in the following cases:

* If it's a complex control script, such as the door opener. Once the script is
  executed, we will switch on the motors and try to open the door. If it's
  already open, you can only rely on the stoppers in the motor controller if
  any. If there are none - the motor will keep moving until the mechanism
  breaks down.  Of course, the motor controller is always equipped with
  stoppers, but it's better to keep it safe than be sorry.

It is impossible in the following cases:

* If you run the actions "on" and "off" in the same way: e.g. to switch on a
  TV-set by sending a signal to IR-controller. A TV-set often has same button
  (and IR signal) for "on" and "off". As a result, we will think that a TV-set
  is "switched on again", but it is switched off instead.
* If you run a command that can damage your equipment or cause an undesirable
  effect when "on" is called for the unit which's already "on": the example can
  be door or motor without any stoppers.
