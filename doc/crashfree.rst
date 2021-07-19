Crash-free setup
****************

Industrial computers are usually turned off without a graceful shutdown. This
may cause database damages or data loss.

EVA ICS uses several mechanisms to protect its data against such accidents.

Inventory configuration
=======================

All configuration is kept inside crash-free :doc:`registry </registry>` and is
protected by default.

Users and API keys
==================

Users and API keys (dynamic) are stored in external databases. As new users and
keys are added rarely, it usually does not cause any errors.

However in production environments it is highly recommended to avoid using
default SQLite databases and switch controllers to either external one or
switch to a more robust one (e.g. `PostgreSQL <https://www.postgresql.org>`_).

Item states
===========

Keeping :doc:`/uc/uc` items (units and sensors) states is usually not
important, as they can be easily restored from the equipment.

Keeping :doc:`/lm/lm` items (lvar) states can sometimes be important as they
may carry logical or custom information.

For both, item state storage can be switched to :doc:`registry </registry>`,
which is slower but much more safe. To switch the controllers, append the
following parameter in "server" section of "config/<controller>/main" registry
key:

.. code:: yaml

    server:
        # ............
        state-to-registry: true

Logs
====

All logs are not considered as the important data and there is no built-in
mechanism to protect them. API call logs can be stored in an external database,
controller logs - on network partitions.
