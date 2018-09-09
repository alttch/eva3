EVA ICS CHANGELOG
*****************

3.1.1 (TBA)
===========

UC
--

    * test-phi CLI tool

3.1.0 (2018-09-01)
==================

UC drivers, device templates, state history, charts and other new features

Core
----

    * working with locks now require allow=lock apikey permission
    * new notifier type: db, used to store item state history
    * SYS API functions: notifiers, enable_notifier, disable_notifier. the
      enable/disable API functions change notifier status only temporary, until
      the controller is restarted
    * MQTT SSL support
    * JSON notifiers. GET/POST notifiers are marked as deprecated and should
      not be used any more.
    * exec function (cmd, run) string arguments splitted with ' ' now support
      the spaces inside (e.g. 'this is "third argument"')

UC
--

    * new uc-cmd cli
    * old uc-cmd renamed to uc-api
    * UC drivers: logical to physical (LPI) and physical (PHI) interfaces
    * native ModBus support (drivers only)
    * device templates
    * new function "state_history" in UC API
    * EVA_ITEM_OID var in the environment of UC scripts
    * action status label (case insensitive) may be used instead of number,
      if the label is not defined, API returns 404 error
    * new key permission: "device", allows calling device management functions.
    * uc-tpl device template validator and generator (alpha)
    * unit and sensor items now have physical location. If location is specified
      as coordinates (x:y or x:y:z), loc_x, loc_y and loc_z props become
      available
    * UC EI now should be enabled/disabled in uc.ini

LM PLC
------

    * new lm-cmd cli
    * old lm-cmd renamed to lm-api
    * macro extensions
    * macro function "unlock" now return false if the lock hasn't been locked
      or doesn't exist
    * unlock macro function may throw an exception if the controller forbids its
      functionality, in case the controller has no master key defined
    * new functions "state_history" in LM API and "history" (equivalent) in
      macros
    * new functions: status, value, nstatus, nvalue with oid support
    * new DM rule events: on nstatus, nvalue change (for units)
    * device management functions: "create_device", "update_device",
      "destroy_device"
    * "set_rule_prop" macro function
    * "alias" macro function
    * rule filter in LM EI
    * LM EI now should be enabled/disabled in lm.ini

SFA
---

    * fixes: rule management functions

    * new sfa-cmd cli
    * sfa-cmd renamed to sfa-api
    * new function "state_history" in SFA API and SFA Framework
    * all functions now accept item oids
    * "result" function returns the result of macro execution if macro action
      uuid or macro id (in the oid format) specified
    * state API function accepts "full" parameter
    * full SFA states now have item descriptions and status labels (for units)
    * SFA API groups function now accept "g" parameter to filter group list
      (with MQTT-style wildcards)
    * SFA rpvt function to load documents from remote servers
    * SFA cvars are automatically available in SFA Framework app. Note: SFA
      cvars are public and may be obtained with any valid API key

    * SFA Framework is now jQuery 3 compatible, included jQuery lib updated to
      3.3.1
    * SFA Framework item states now also have description and status labels
      fields
    * eva_sfa_groups function, returns item groups list (with optional filter)
    * eva_sfa_chart function, displays item state charts
    * eva_sfa_popup function, displays popups and info windows
    * new ws event: server restart and eva_sfa_server_restart_handler in a
      framework. SFA API function "notify_restart" allows to notify clients
      about the server restart w/o actual restarting (e.g. when restarting
      frontend)

    * jinja2 templates for SFA ui and PVT files (all files with .j2 extension
      are served as templates). index.j2 has more priority than index.html

API Client
----------

    * new API function call result: "result_invalid_params" (11)

Common
------

    * new notifier management CLI (old CLI tools available in **legacy** folder)
    * watchdog to test/automatically restart controllers in case of failure
    * oid support in API keys
    * other stability improvements

3.0.2 (2018-06-23)
==================

Bugfix release, some new urgent features, stability improvements

EVA documentation is now available in reStructuredText format and at
https://eva-ics.readthedocs.io

Emergency interfaces
--------------------

    * fixes: correct display of long item names
    * fixes: various bug fixes
    * refresh buttons on item pages
    * LM EI: reset button and expire timer in LM EI show/hide when prop changed

Core
----

    * fixes: remove empty controller group when all objects are deleted
    * fixes: remote items correctly display state in list_remote
    * fixes: disabled sensors and lvars should not react to expiration
    * each set_prop call now logs what's actually changed
    * added item oid (type:group/item_id) - reserved for the future releases
    * added stop_on_critical option in config (default: yes),
      server will be restarted via safe-run if critical exception occur
    * uptime in dump and test API function, last 100 exceptions are now stored
      in a dump, dumps are now compressed with gzip
    * API functions now support JSON requests

UC
--

    * action_toggle function to quickly toggle status of simple units 

LM PLC
------

    * list_remote returns array + controller_id proprety instead of dict
    * result function in macro api. terminate and result function accept action
      uuid as a param
    * on_set lm rule (status changed to 1)
    * new LM API and macro functions: clear (set lvar value to 0), toggle
      (toggles lvar value between 0 and 1)
    * cmd macro function now accepts full controller id (uc/controller_id) as
      well as short
    * new macro functions for file management: ls, open_oldest, open_newest

SFA
---

    * fixes: dm_rule_props acl in SFA

    * list_remote returns array instead of dict + controller_id proprety
    * list_macros contains now controller property
    * append_controller now tries to autodetect controller type if no type
      is specified
    * sfa pvt access logs
    * reset, toggle, clear, action_toggle, result and terminate by uuid funcs in
      sfa & sfa framework
    * reload_clients command and sfa framework reload event handler
    * eva_sfa_expires_in function in a framework to work with timers
    * log processing functions in a framework
    * wildcard masks in eva_sfa_state and eva_sfa_register_update_state

Common
------

    * easy-setup.sh - an interactive/automatic script to quickly set up the
      current host
    * ability to run controllers under restricted user

3.0.1 (2018-02-21)
==================

Minor release with some urgent features

Core
----

    * EVA_ITEM_PARENT_GROUP variable in script ENV which contains the parent
      group of the item
    * cvars now can be set as global or assigned to the specified item group
      i.e. 'VAR1' - global cvar, available to the all scripts,
      'group1/VAR2' - variable available only to scripts from group
      'group1' (as 'VAR2'), 'group2/VAR2' - variable available only to
      group 'group2' (also as 'VAR2').  Used by UC scripts to let one
      script manage different items

UC
--

    * 'update_delay' prop - item passive update may start with a delay to
      prevent multiple updates running simultaneously producing high system
      load
    * 'clone' function in UC API and uc-cmd to clone items
    * 'clone_group' function - clones all matching items in a group
    * 'destroy_group' function destroys all items in the specified group

LM
--

    * item id in LM rules match by simple mask (i.e. '\*id\'* or 'id\'* or
      '\*id')

3.0.0 (2017-10-19)
==================

First public release
