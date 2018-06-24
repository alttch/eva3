EVA ICS CHANGELOG
=================

3.0.3
-----

Core:

    * working with locks now require allow=lock apikey permission
    * new notifier type: db, used to store item state history

UC:
    * new function state_history in UC API

LM:
    * macro function unlock now return false if lock was not locked or doesn't
      exist
    * unlock macro function may throw exception if the controller forbids it's
      functionality, in case the controller has no masterkey defined
    * new functions "state_history" in LM API and "history" (equivalent) in
      macros

SFA:
    * fixed rule management functions
    * new function state_history in SFA API
    * state and state_history functions accept item oids
    * SFA framework is now jQuery 3 compatible, jQuery lib updated to 3.3.1

3.0.2
-----

Bugfix release, some new urgent features, stability improvements

EVA documentation is now available in reStructuredText format and at
https://eva-ics.readthedocs.io

Emergency interfaces

    * fixes: correct display of long item names
    * fixes: various bug fixes
    * refresh buttons on item pages
    * LM EI: reset button and expire timer in LM EI show/hide when prop changed

Core:

    * fixes: remove empty controller group when all objects are deleted
    * fixes: remote items correctly display state in list_remote
    * fixes: disabled sensors and lvars should not react to an expiration
    * each set_prop call now logs what's actually changed
    * added item oid (type:group/item_id) - reserved for the future releases
    * added stop_on_critical option in config (default: yes),
      server will be restarted via safe-run if critical exception occur
    * uptime in dump and test API function, last 100 exceptions are now stored
      in a dump, dumps are now compressed with gzip
    * API functions now support JSON requests

UC:

    * action_toggle function to quickly toggle status of the simple units 

LM PLC:

    * list_remote returns array + controller_id proprety instead of dict
    * result function in macro api. terminate and result function accept action
      uuid as a param
    * on_set lm rule (status changed to 1)
    * new LM API and macro functions: clear (set lvar value to 0), toggle
      (toggles lvar value between 0 and 1)
    * cmd macro function now accepts full controller id (uc/controller_id) as
      well as short
    * new macro functions for the file management: ls, open_oldest, open_newest

SFA:

    * fixes: dm_rule_props acl in SFA

    * list_remote returns array instead of dict + controller_id proprety
    * list_macros contains now controller property
    * append_controller now tries to autodetect controller type if no type
      specified
    * sfa pvt access logs
    * reset, toggle, clear, action_toggle, result and terminate by uuid funcs in
      sfa & sfa framework
    * reload_clients command and sfa framework reload event handler
    * eva_sfa_expires_in function in a framework to work with timers
    * log processing functions in a framework
    * wildcard masks in eva_sfa_state and eva_sfa_register_update_state

Common:

    * easy-setup.sh - an interactive/automatic script to quickly set up the
      current host
    * ability to run controllers under restricted user

3.0.1
-----

Minor release with some urgent features

Core:

    * EVA_ITEM_PARENT_GROUP variable in script ENV which contains the parent
      group of the item
    * cvars now can be set as global or assigned to the specified item group
      i.e. 'VAR1' - global cvar, available to the all scripts,
      'group1/VAR2' - variable available only to scripts from group
      'group1' (as 'VAR2'), 'group2/VAR2' - variable available only to
      group 'group2' (also as 'VAR2').  Used by UC scripts to let one
      script manage different items

Universal Controller:

    * 'update_delay' - item passive update may start with a delay to prevent
       multiple updates run simultaneously producing high system load

UC API and uc-cmd:

    * 'clone' function in UC API and uc-cmd to clone items
    * 'clone_group' function in UC API and uc-cmd for cloning all matching
       items in a group
    * 'destroy_group' function destroys all items in the specified group

Logic Manager:

    * item id in LM rules match by simple mask (i.e. '\*id\'* or 'id\'* or
      '\*id')

3.0.0
-----

First public release
