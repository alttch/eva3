Registry database
*****************

Starting from the version 3.4, EVA ICS uses structured document database as the
primary storage of all configurations. In EVA ICS it is called "document
registry system" or just "registry".

.. contents::

Technology
==========

EVA ICS uses `YEDB <https://www.yedb.org>`_ as the structured database. YEDB is
fast, easy to repair and crash-free.

Registry server is started with "/opt/eva/sbin/registry-control start" and MUST
be always online. When YEDB is upgraded, all EVA ICS components should be
stopped (vendor-provided upgrade scripts stop everything automatically).

Registry can be managed with "eva-registry", "eva registry manage" and
"sbin/eva-registry-cli" :doc:`command-line</cli>` tools.

Reasons
=======

Why did EVA ICS switch to the registry database, instead of using simple "ini"
and "json" files:

* Crash-free storage of configurations, inventory and data objects;
* easy management with command line tools and API;
* strict data schemas;
* unification;
* easy-to-use SDK.

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

If configuration file is not created, EVA ICS starts and uses registry server
with the default settings.

Maintenance
===========

When deploying / undeploying lots of :doc:`items</items>`, old registry keys
are not deleted but moved to the database trash. It is a good idea to clean it
from time to time wit "eva-registry purge" or "registry_safe_purge" API method.

".trash" folder can also be used to restore keys deleted by accident.

When key data is changed, the server keeps its 10 backup copies by default,
which can be also used to restore data if necessary.

To list deleted and backup copies, use "ls -a" command of "eva-registry" tool.

All data is stored in "runtime/registry" directory, which should
not be accessed directly, unless data loss occur.

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
config/uc/defaults                   yes           item defaults
config/lm/defaults                   yes           item defaults
config/inventory                     not rec.      inventory key (EVA ICS items)
config/data                          forbidden     system objects
config/userdata                      yes           any user-defined data
==================================== ============= ================================

SDK
===

**eva.registry** module provides functions for registry management. All
functions set key prefix ("eva3/<SYSTEM_NAME>/") automatically.

The module can be imported and used in :doc:`plugins</plugins>`, :doc:`LM PLC
macros </lm/macros>` or anywhere else. When imported by 3rd-party scripts with
EVA ICS "lib" directory added to the import path, the module automatically
initializes itself with the proper system name and connection settings from
"eva_config" file.

.. include:: ./pydoc/pydoc_registry.rst

Module variables:

 * **SYSTEM_NAME** name of the current node

 * **db** `YEDB Python <https://github.com/alttch/yedb-py>`_ object, can be used
   e.g. to manipulate keys without auto-prefixing.

It is also possible to work with registry server using the official API and
clients. See https://www.yedb.org/ for more details.
