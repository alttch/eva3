EVA ICS CHANGELOG
*****************

3.4.2 (TBA)
===========

Common
------

    * CLI client SSL verify is now on by default. To suppress SSL certificate
      verification, manually set URL as "!https://..."
    * State registry keys are not auto backed up any longer
    * New API method "check_item_access"
    * Custom suicide timeouts
    * Poll delay allowed to be set to 1 microsecond
    * Fix for UDP notifier data frames longer than 65K

LM PLC
------

    * new rules option: "block on exec" (blocks decision matrix until a macro
      is completed).
    * plc/rule-masks-enabled option allows to turn off rule masks (except
      simple '#' masks for all groups/types/ids), which speeds up rule
      processing

3.4.1 (2021-09-06)
==================

Common
------

   * fix: recombined ACLs speed tuning
   * fix: db updates on-exit correct transactions commit/rollback
   * fix: MQTT auth in setup, check-mqtt

   * item states can be kept in the crash-free registry
   * controller PIDs in "test" command (requires master key)
   * launch pptop directly from eva-shell
   * new API method "restart_notifier"
   * stricter MQTT notifier tests, pingers restart notifiers if failed
   * dump "-m" option to create minimal dumps on large systems
   * new API method "get_exceptions", allows to get last 100 server exceptions
     even if they are disable in logs
   * IEID phantom state - when a remote controller is disconnected, its items
     have IEIDs [0,0]

3.4.0 (2021-07-07)
==================

Common
------

   * fix: correct backups of symlinked directories
   * fix: PVT backup
   * fix: "dump" on Python 3.9.5+

   * Configs and runtime data moved to crash-free YEDB-based registry
   * Next-generation event replication engine
   * Python virtual environment directory renamed to "venv"
   * plugins and custom drivers / extensions moved to "runtime"
   * InfluxDB v2 support (v1 API via dbrp and v2 API)
   * TimescaleDB support
   * "connected" property of the remote items in LM PLC and SFA
   * UDP Notifiers
   * LURP event replication protocol
   * Notifier event buffering
   * "eva backup restore" now stops / starts all components automatically if
     runtime folder is restored.
   * new API method: registry_safe_purge (clears registry trash but keeps
     broken keys)
   * "ssl-force-redirect" option for WebAPI (GET methods only)
   * new feature quick setup/remove: ssl, node_name
   * filter log records by regex
   * Plugins API v3: "handle_api_call", "handle_api_call_result" method to
     intercept API calls
   * client ids and "get_neighbor_clients" API method (requires EVA JS Framework
     0.3.24+)
   * notifier frame counter and online info with "notifier list" CLI command
   * Alpine Linux support (3.13+)
   * OWFS feature installs libow from source if no package exists
   * Built-in PyPi mirror option to forcibly download sources of all modules
   * "auto-save" option, auto-save is on by default
   * "pip_install" function in core scripts automatically appends modules to
     venv config

UC
--

   * item "update_delay" property is returned back
   * unit actions check value ranges if defined
   * "randomize" and "increment" auto modify for virtual sensor driver
   * data puller states, data pullers can be created / destroyed without the
     controller restart, new API methods "create_datapuller",
     "destroy_datapuller"
   * Number type support in "get_modbus_slave_data" API function and
     "modbus-slave get" CLI commands
   * customizable default configuration for units and sensors

LM PLC
------

   * Discover controllers as static
   * customizable default configuration for lvars

SFA
---

   * Locale files can be stored in both "pvt" and "ui"
   * Custom UI error pages
   * Deployment error codes explanation
   * "reboot_controller" special deployment API function
   * Serving public and private structured data from EVA ICS Registry
   * Discover controllers as static

Removed and deprecated
----------------------

    * deprecated: running EVA ICS controllers under different users

    * supervisord support is no longer out-of-the-box, however control scripts
      still accept the corresponding settings (will be removed in 3.5)
    * <controller>-control scripts are removed. Use "eva <controller>" instead.
    * mailer configuration unified for all components
    * removed "nodename" option of eva-shell.ini

3.3.2 (2021-03-01)
==================

Common
------

    * RedHat Enterprise Linux 8 is now officially supported

    * fix: hosts_allow / hosts_assign in JRPC calls
    * fix: cmd wait delay
    * fix: allow ACL OID groups without masks
    * fix: test command don't report number of active threads any more for
      API keys without "sysfunc" permission

    * fix: JSON logging
    * fix: improved stability of controller pools

    * deprecated: RESTful and direct API, including CS_EVENT_API in Core scripts

    * 1-Wire OWFS libraries are now optional by default

    * Python 3.9 support
    * local mirror feature (mirroring EVA ICS repo and PyPi)
    * packages deployment
    * "feature setup/remove" - execute common setup tasks with a single command
      from EVA shell.
    * "value" field in state and history databases increased to 8192 bytes
    * cmd API function accepts args as a list
    * cmd API function accepts STDIN data
    * xc/cmd moved to runtime
    * file get/put functions support of binary data
    * install option "--skip-venv". "--skip-check" no longer skips venv building
    * deep code audit and tons of bug fixes
    * Core scripts:
        * new event CS_EVENT_SYSTEM (invoked on startup / shutdown)
        * new event CS_EVENT_RPC (replaces deprecated CS_EVENT_API)
        * new event CS_EVENT_PERIODIC
        * logger object
    * Core Plugins API v2, new functions:
        * create_db_engine
        * format_db_uri
        * get_thread_local
        * has_thread_local
        * set_thread_local
        * clear_thread_local
        * sendmail
    * "set_user_password" SYS API function now allows logged in users to change
      their passwords
    * "list_tokens"/"drop_tokens" API functions
    * state_history API function can return data for disconnected / deleted
      items
    * new argument for state_history: z (time zone)
    * update with pre-downloaded tarballs
    * mailer feature available in all controller types (used by core plugins)
    * "cdata" (custom data) API key field
    * "file_put" method automatically creates required directories
    * "shutdown_core" method now executes background shutdown, plus has got an
      extra option "t" to specify shutdown delay (useful for MQTT API call)
    * "import_module" function in cloud deployment and device template files
    * "history" CLI command bar charts output
    * "watch" CLI command
    * "slog" CLI command (displays state log)
    * JSON RPC additionally accepts requests to the root URI (required by some
      clients), accepts and trying to fix malformed requests
    * JSON RPC API via HTTP GET
    * Active Directory credentials caching
    * user ACL combining
    * items_deny / groups_deny key ACL properties
    * Read-only mode for tokens, "set_token_readonly" API function
    * MQTT notifiers: ping interval to auto-restore connection
    * MQTT notifiers: subscribe_all option
    * db notifiers: simple cleaning
    * signed releases

UC
--

    * fix: Modbus/UDP (server) packet processing
    * fix: Modbus serial custom byte size
    * fix: update_if_action logic

    * deprecated: old format of device templates
    * deprecated: multi-update scripts
    * deprecated: direct eva.uc.modbus import in Modbus PHIs
    * deprecated: direct eva.uc.owfs import in OWFS PHIs

    * data pullers
    * DriverAPI v10: Modbus and OWFS helper tools
    * UC API: new function "state_log"
    * auto_off unit state processor can be cancelled / modified while running
    * "server cleanup" CLI command (cleans state db)
    * new device template format (equal to IaC deploy)
    * default timeout for Modbus / OWFS reduced to 1s to avoid critical events
    * unit MQTT control / update commands can be sent in JSON
    * strict device deployment files schema check (new format only)
    * Modbus virtual port API methods and CLI data types (u16, i16, u32, i32,
      u64, i64, f64) and bit getters / setters

LM PLC
------

    * fix: "out" variable is now correctly set if macro raises an exception

    * new config option "plc/use_core_pool"
    * LM API: new function "state_log"
    * LVar variable logic: normal (default) or simple
    * SSL, TLS and SMTP auth support for mailer
    * macro function "cmd": new argument "stdin_data"
    * macro function "sha256sum"
    * macro function "get_directory"
    * decision rules prop "for_prop_bit" to check individual bits
    * CLI/API option to auto-enable created rules/jobs
    * CLI: quick creation of rules with no condition
    * LVar deletion by group ("destroy_lvar" API method and CLI)
    * Cache remote state for LM PLC items

SFA
---

    * SFA API: new function "state_log"
    * PVT serving as /pvt/path/to/file
    * File uploads
    * connected controllers in "test" API method (*$eva.server_info.connected*
      in EVA JS Framework)
    * data serve as locale support
    * cloud deploy: "status" and "value" props in deployment files
    * cloud deploy: trigger item update after deployment
    * cloud deploy: module uploads and binary files support
    * cloud deploy: skip busy drivers/PHIs during undeployment
    * cloud deploy: skip existing items during deployment (optionally)
    * cloud deploy: local functions ("sleep", "system")
    * cloud deploy: local cloud manager API calls and "local" controller
      section
    * cloud deploy: file masks in upload-remote
    * cloud deploy: accepts deployment YAML from STDIN
    * cloud deploy: custom before/after deploy timeouts
    * cloud deploy: API keys and local user accounts deployment
    * strict device deployment files schema check
    * cloud updates


3.3.1 (2020-08-26)
==================

Common
------

    * fix: auth tokens are now always correctly destroyed at logout
    * new generic extension engine: restarting controller after PHI, LPI & LM
      PLC Ext module updates is no longer necessary (just load the new module)
    * "interval" notifier property allows to schedule item state telemetry
      notifications with the specified time interval.
    * MS Active Directory authentication support
    * custom primary log formats (e.g. JSON logs)
    * extended API logging, ACI (API Call Info) core object, "api_log_get" SYS
      API function
    * Core plug-ins
    * JSON notifiers "list" method to send all data in list format

UC
--

    * Added "enable" flag in API and CLI to enable unit actions / sensor updates
      right after creation.
    * Driver API 9: PHI & LPI mods config validation, Ethernet/IP client helper


LM PLC
------

    * Extension API 7: config validation

SFA
---

    * supervisor features: API lock/unlock, broadcast messages
    * SFA templates "get_aci" and "import_module" functions
    * before/after deploy API calls can be skipped in case of failure


3.3.0 (2020-02-05)
==================

Common
------

   * Faster node interconnect protocol (via msgpack)
   * MQTT inter-connect API encryption strength increased to AES256
   * Core workers are now async to improve system performance
   * Controller auto-discovery in local network via UPnP
   * Core scripts

UC
--

   * Fixed PHI update timers
   * push_phi_state API method
   * Driver API 8: timeout helper, PHI state push
   * item "update_delay" property is removed

LM
--

   * Fixed cycle timers. As new cycle algorithm has near 100% precision, "avg"
     is not reported any longer. "value" field in API response is removed as
     well.
   * Extension API v6: persistent data storage


3.2.5 (2019-10-03)
==================

Common
------

    * Google Cloud IoT Core support

    * fix: startup timeouts

LM PLC
------

    * Rule chill-out logic corrected

Cloud manager
-------------

    * First public beta


3.2.4 (2019-07-30)
==================

Common
------

    * Core and controller interconnect stability improvements
    * IOTE cloud support
    * InfluxDB integration
    * Prometheus integration
    * Logging to syslog
    * Autocompletion files for ZSH
    * server events
    * CLI edit command for controller server config

UC
--
    * Driver API 7: shared namespaces

LM PLC
------

    * Direct use of macro functions (as @function)
    * rule, job and cycle creation with human readable input

SFA
---

    * edit ui / edit pvt commands in EVA shell


3.2.3 (2019-06-24)
==================

Common
------

    * MQTT server is not required anymore for local host/network installations,
      controllers can exchange information in real-time via P2P sockets (turned
      on automatically if MQTT server for controller is not specified).
    * state_history method can now return chart image (SVG/PNG)

UC
--

    * get_phi_ports API method - get ports of loaded PHI
    * phi_discover API method - search for equipment supported by PHI module
    * Modbus values reported to UC slave can now be automatically converted to
      signed and divided (or multiplied).

LM PLC
------

    * set_job_prop macro function
    * cycle can now run macros with args and kwargs

SFA
---

    * easy-setup now creates default user (operator)
    * "as" parameter for .json and .yml files changes their format on the flow
    * JS SFA Framework is now deprecated. Use EVA JS Framework instead:
      https://github.com/alttch/eva-js-framework


3.2.2 (2019-05-21)
==================

UC
--

    * Driver API 5: "unload" method, unit values in PHIs.

LM PLC
------

    * scheduled jobs

SFA
---

    * evaHI integration
    * transparent authentication on secondary UI pages


3.2.1 (2019-04-16)
==================

Common
------

    * fixes: small fixes in CLI
    * fixes: code refactoring, performance optimization

    * EVA ICS now loads 3rd party libraries from virtualenv which increases
      system stability as only tested version of libraries are used.
    * Support for AWS IoT
    * Modbus slave register monitoring functions
    * increment/decrement functions for lvars and shared macro variables
    * read-only permissions for API keys


3.2.0 (2019-04-02)
==================

Common
------

    * Core, API and CLI performance improvements

    * fixes: correct backup/restore if configuration folders are symlinks
    * fixes: correct restore if --runtime flag is specified
    * fixes: LM PLC locking problems

    * notifier performance improvements
    * CLI improvements

    * private Cloud support (nodes run API calls via MQTT)
    * automatic node discovery
    * license changed to Apache License 2.0
    * new SYS API function: shutdown_core
    * controller/node autodiscovery
    * enterprise layout is now default item layout
    * using item ids in API key properties is not allowed any longer in
      enterprise layout, item oid (type:group/id) must always be specified
    * X-Auth-Key header authorization support
    * JSON RPC 2.0 API
    * JSON notifiers will send JSON RPC 2.0 notifications to the target uri, if
      *method* param is set
    * RESTful API
    * API session tokens
    * Database support for MySQL and PostgreSQL
    * supervisord support

UC 
--

    * warning: API function *set_driver* renamed to *assign_driver*

    * new API functions: list_device_tpl, set_driver_prop, set_phi_prop
    * 1-Wire OWFS support (virtual buses, PHIs), OWFS API functions

    * Modbus slave support
    * Driver API v4

LM PLC
------

    * new API functions: enable_controller, disable_controller,
      matest_controller, set_ext_prop
    * kwargs in macros (kwargs dict, plus all keyword arguments are available
      as variables)
    * set_rule_prop now accepts "condition" and "for_oid"
    * cycles, cycle control API and macro functions
    * removed deprecated dm_rule* ACL
    * removed deprecated get/post functions (use requests.get/post instead)
    * Extension API v4

SFA
---

    * new API functions: enable_controller, disable_controller, list_cycles
    * SFA framework: code optimization, cycle states (warning: some functions
      are incompatible with previous version, use eva_sfa.3.1.js library or
      call the functions in new format only, look UPDATE.rst for more info)
    * SFA framework: data exchange optimization with eva_sfa_state_updates
      variable
    * removed deprecated dm_rule* ACL and rule control functions
    * SFA templates: **request** now contains full request object
    * SFA templates: new function api_call (call any SFA API method)

Deprecated (will be removed in 3.3.0)
-------------------------------------

    * macro "argv" variable (replaced with "args")
    * PHP API client no longer supported (use JSON RPC)
    * removed deprecated HTTP/POST and HTTP/GET notifiers


3.1.1 (2018-10-22)
==================

Common
------

    * fixes: interactive prompt behavior
    * fixes: API client libs check result of "phi_test" and "phi_exec"
      functions 

    * history for interactive shell mode (to turn off set
      EVA_CLI_DISABLE_HISTORY=1 system environment variable)
    * new management CLI: eva-shell (interactive by default)
    * backup/restore operations (with eva-shell)
    * dynamic API key management via CLI and API

UC
--

    * fixes: device commands in enterprise layout
    * performance improvements

    * "update" command without params starts item passive update
    * batch commands in UDP API (separated with new line) 
    * encryption and authentication in UDP API
    * custom packet handlers in UDP API
    * new API function: "test_controller", detailed info in "list controllers"
    * MQTT tools for PHIs
    * test-phi CLI tool

LM PLC
------

    * fixes: double quoted macro arguments in DM rules
    * fixes: gain param in "tts" and "audio" extensions

    * "action_toggle" macro func, "toggle" acts as an alias for unit oids
    * "shared" and "value" macro funcs default return values
    * new API function: "test_controller", detailed info in "list controllers"
    * new LPI: usp (unit single port)
    * test-ext CLI tool

SFA
---

    * new API function: "test_controller", detailed info in "list controllers"
    * SFA framework fixes and improvements


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
    * exec function (cmd, run) string arguments split with ' ' now support
      the spaces inside (e.g. 'this is "third argument"')

UC
--

    * new uc-cmd cli
    * old uc-cmd renamed to uc-api
    * UC drivers: logical to physical (LPI) and physical (PHI) interfaces
    * native Modbus support (drivers only)
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

    * list_remote returns array + controller_id property instead of dict
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

    * list_remote returns array instead of dict + controller_id property
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

LM PLC
------

    * item id in LM rules match by simple mask (i.e. '\*id\'* or 'id\'* or
      '\*id')


3.0.0 (2017-10-19)
==================

First public release
