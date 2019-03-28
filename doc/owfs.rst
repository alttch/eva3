OWFS (1-wire)
*************

:doc:`/uc/uc` provides native support of `1-wire
<https://en.wikipedia.org/wiki/1-Wire/>`_ technology for OWFS :doc:`physical
interfaces (PHIs)</drivers>`. Core support is provided with `OWFS
<http://owfs.org/>`_.

For the simple setups, when 1-wire bus is connected via system GPIO, PHIs can
access it directly. But when 1-wire is accessed via I2C, USB or other external
bus, OWFS is preferred.

EVA ICS provides additional functionality for OWFS, such as bus locking,
automatic retry attempts, virtual ports for drivers etc.

Defining OWFS bus
=================

Before using any OWFS PHI, you must define OWFS bus. OWFS  PHIs work with
defined buses only, while UC handles all hardware calls and responses.

List of the defined OWFS buses be obtained with command:

.. code-block:: bash

    uc-cmd owfs list

To define new OWFS bus, execute the following command:

.. code-block:: bash

    uc-cmd owfs create [-h] [-l] [-t SEC] [-r RETRIES] [-d SEC] [-y] ID LOCATION

where:

* **-l** lock bus on operations, which means to wait while OWFS bus is
  used by another controller thread (driver command)

* **-t SEC** operations timeout (in seconds, default: default timeout)

* **-r RETRIES** retry attempts for each operation (default: no retries)

* **-d SEC** delay between operations (default: 50ms)

* **-y** save OWFS config after creation

* **ID** bus ID which will be used later in :doc:`PHI</drivers>` configurations

* **LOCATION** OWFS location

OWFS location should contain the configuration of OWFS port. Actually it's
equal to standard OWFS params, except first *--* are not required:

.. code-block:: bash

    # defines owfs bus on I2C#1
    uc-cmd owfs create local1 "i2c=/dev/i2c-1:ALL" -y
    # defines owfs bus on I2C#0 (force)
    uc-cmd owfs create local2 "/dev/i2c-0 --w1" -y
    # define owfs bus on local owserver
    uc-cmd owfs create local3 localhost:4304 -y

As soon as the bus is defined, it can be used by PHI.

.. code-block:: bash

    uc-cmd owfs scan local1 -a PIO
    # 05.4AEC29CDBAAB  DS2405
    uc-cmd phi load relay1 ow_ds2405 -c owfs=local1,path=05.4AEC29CDBAAB -y

As the result, controller creates a :doc:`driver</drivers>` *relay.default*
which can be set to :doc:`item</items>`.

.. warning::

    UC will grant OWFS bus access to PHI only if it has enough timeout to
    wait for the longest possible call. It means operation timeout
    (**action_timeout**, **update_timeout**) in :doc:`item</items>` should be
    greater than *owfs_bus_timeout*(1+owfs_bus_retries)*. If the
    command max timeout is less than this value, attempts to access OWFS
    bus return an error.

If you need to change OWFS bus params or options, you can always define new
OWFS bus with the same ID, without deleting the previous one. Bus configuration
and options will be overwritten.

Scanning OWFS for devices
=========================

With *scan* command you can scan OWFS bus for the devices which have e.g.
specified attributes:

.. code-block:: bash

    uc-cmd owfs scan <ID> [options]
    # e.g. let's find all 1-wire equipment which has "temperature" property:
    uc-cmd owfs scan local1 -a temperature

Deleting OWFS bus
=================

To delete (undefine) OWFS bus, execute the command:

.. code-block:: bash

    uc-cmd owfs destroy <ID>
    # e.g.
    uc-cmd owfs destroy local1

Note that controller doesn't check if the port is in use or not, so double
check this manually before deleting it.

Also note that some bus types lock system **ow** libraries and can not be
recreated until :doc:`/uc/uc` process is restarted.

