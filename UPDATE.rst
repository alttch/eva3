EVA ICS 3.2.0
=============

What's new
----------

* JSON RPC and RESTful API
* Cloud support (MQTT node autodiscovery)
* Speed and stability improvements
* OWFS support
* ModBus slave

Complete change log: https://get.eva-ics.com/3.2.0/stable/CHANGELOG.html

Preparing
---------

Before applying this update

* test your key items and macros/scripts in a test sandbox
* make full backup of EVA ICS folder

* install **libow** and **libow-dev** system packages
* install **jq** console JSON parser tool
* set notifier DBs (if used) to absolute path
* default item layout is not enterprise, if using simple - specify this in
  configs
* sessions are off now by default, if user logins are used - turn them by
  setting session_timeout > 0 in configs
* set SFA ui to use js/eva_sfa.3.1.js until ported. The following SFA FW
  function calls are INCOMPATIBLE with previous version:

    * eva_sfa_action
    * eva_sfa_action_toggle
    * eva_sfa_chart
    * eva_sfa_groups
    * eva_sfa_popup
    * eva_sfa_result
    * eva_sfa_run
    * eva_sfa_state_history
