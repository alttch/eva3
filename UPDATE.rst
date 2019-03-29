EVA ICS 3.2.0
*************

What's new
==========

* JSON RPC and RESTful API
* Cloud support (MQTT node autodiscovery)
* Speed and stability improvements
* OWFS support
* ModBus slave

Complete change log: https://get.eva-ics.com/3.2.0/stable/CHANGELOG.html

Update instructions
===================

Before update
-------------

Before applying this update

* test your key items and macros/scripts in a test sandbox
* make full backup of EVA ICS folder

* install **libow** and **libow-dev** system packages
* install **jq** console JSON parser tool
* set notifier DBs (if used) to absolute path
* default item layout is now enterprise, if using simple - specify this in
  configs
* Custom LM PLC extensions are not compatible with v4 API used in 3.2.0 and
  should be ported before update (tiny constructor modification required) * UC
  PHI, developed for Driver API v1 are no longer compatible. Switch them to v4
  or at least add __equipment__ field.
* sessions are off now by default, if user logins are used - turn them by
  setting session_timeout > 0 in configs.
* SFA templates **request** variable now contains full request object. To get
  request parameters, access them with *request.params*.
* set SFA UI to use js/eva_sfa.3.1.js until ported. The following SFA FW
  function calls are INCOMPATIBLE with previous version:

    * eva_sfa_action
    * eva_sfa_action_toggle
    * eva_sfa_chart
    * eva_sfa_groups
    * eva_sfa_popup
    * eva_sfa_result
    * eva_sfa_run
    * eva_sfa_state_history

* if update script fails to install new modules, update existing manually.
  Modules with known issues and update commands for them:

    * pip3 install -U pyasn1

After update
------------

Enabling Cloud API/autodiscovery
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For each controller, set notifier **eva_1** properties:

* **discovery_enabled** true
* **api_enabled** true
* **announce_interval** 30

Create equal API key named **default** on each controller.

Enabling Cloud Manager
~~~~~~~~~~~~~~~~~~~~~~

* append section *[cloud]* and prop *cloud_manager = yes* to
  etc/sfa.ini
* set *masterkey* property for each controller, connected to SFA

