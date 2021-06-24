Registry database
*****************

Starting from the version 3.4, EVA ICS uses structured document database as the
primary storage of all configurations. In EVA ICS it is called "document
registry system" or just "registry".

.. toctree::

Technology
==========

EVA ICS uses `yedb <https://www.yedb.org>`_ as the structured database. YEDB is
fast, easy to repair and crash-free.

Registry server is started with "/opt/eva/sbin/registry-control start" and MUST
be always online. When YEDB is upgraded, all EVA ICS components should be
stopped (vendor-provided upgrade scripts stop everything automatically).

Registry can be managed with "eva-registry", "eva registry manage" and
"sbin/eva-registry-cli" :doc:`command-line</cli>` tools.

Reasons
=======

* Crash-free storage of EVA ICS configuration files, inventory and data
  objects.
* Easy management with command line tools and API.
* Strict data schemas.
* Unification.

Configuration
=============

YEDB configuration is defined in "etc/eva_config".

.. literalinclude:: ../etc/eva_config-dist
    :language: shell

It is also possible to use a single registry database for different EVA ICS
nodes. if "YEDB_SERVER_ENABLED" is set to "0", the server is not stared/stopped
locally.

.. warning::

    It is highly recommended to keep strict data schema (enabled by default).

Maintenance
===========

When deploying / undeploying lots of :doc:`items</items>`, old registry keys
are not deleted but moved to the database trash. It is a good idea to clean it
from time to time wit "eva-registry purge" or "registry_safe_purge" API method.

".trash" folder can also be used to restore keys deleted by accident.

When key data is changed, the server keeps its 10 backup copies by default,
which can be also used to restore data if necessary.

To list deleted and backup copies, use "ls -a" command of "eva-registry" tool.

All data is stored in "runtime/registry" directory, which should not be
accessed directly, unless data loss occur. If repair with built-in management
tools.

Structure
=========

Each EVA ICS node creates registry key "eva3/<SYSTEM_NAME>", all data is being
stored in its sub-keys.

A strict schema ".schema/eva3/<SYSTEM_NAME>" is created for all data keys,
except "userdata" key, which (as well as its subkeys) can contain any fields.

Keys can be edited with "eva-registry" and "eva-registry-cli" :doc:`CLI</cli>`
tools.

==================================== ============= ================================
Key                                  user-editable Description
==================================== ============= ================================
config/common/mailer                 yes           mailer configuration
config/watchdog                      yes           controller watchdog
config/venv                          yes           venv configuration
config/<controller>/main             yes           primary controller configuration
config/<controller>/apikeys/<key>    yes           static API keys
config/<controller>/service          may           startup configuration
config/<controller>/plugins/<plugin> yes           plugin configuration
config/uc/datapullers/<datapuller>   may           datapuller configuration
config/uc/drivers                    not rec.      UC drivers
config/uc/defaults/unit              yes           defaults for units
config/uc/defaults/sensor            yes           defaults for sensors
config/lm/defaults/lvar              yes           defaults for lvars
config/inventory                     not rec.      inventory key (EVA ICS items)
config/data                          forbidden     system objects
config/userdata                      yes           any user-defined data
==================================== ============= ================================
