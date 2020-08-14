EVA ICS 3.3.1
*************

What's new
==========

* Active directory support
* extended API logging
* Core plug-ins
* SFA supervisor locks

Complete change log: https://get.eva-ics.com/3.3.1/stable/CHANGELOG.html

Update instructions
===================

New UC Driver and LM Extensions API require strict validation of module params
(config, state / action for UC drivers) if supported by module. All modules
included in EVA ICS default distribution, have got validation support built-in.

After applying update, controller error log should be checked as well as list
of loaded drivers / extensions. In case of errors, stop the controller,
manually edit *runtime/uc_drivers.json* and *runtime/lm_extensions.json*,
correct invalid parameters and start it again.
