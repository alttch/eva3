ModBus
******

:doc:`/uc/uc` provides native support of `ModBus <http://www.modbus.org/>`_
protocol for ModBus :doc:`physical interfaces (PHIs)</drivers>`. Core support
is provided with `pymodbus <https://pymodbus.readthedocs.io>`_ Python module,
but with additional functionality, such as bus locking, automatic retry
attempts, virtual ports for drivers etc.

:doc:`/uc/uc` works as ModBus master, connection links to all slave devices
should be defined as virtual ports. After that, defined virtual ports and
ModBus unit IDs should be set in corresponding :doc:`PHI modules</drivers>`
load configurations.

Defining ModBus virtual port
============================

Before using any ModBus PHI, you must define ModBus virtual port. ModBus PHIs
work with ModBus virtual ports only, while UC handles all hardware calls and
responses.

List of the defined ModBus virtual ports can be obtained with command:

.. code-block:: bash

    eva uc modbus list

To create new ModBus virtual port, execute the following command:

.. code-block:: bash

    eva uc modbus create [-l] [-t SEC] [-r RETRIES] [-d SEC] [-y] ID PARAMS

where:

* **-l** lock port on operations, which means to wait while ModBus port is
  used by another controller thread (driver command)

* **-t SEC** ModBus operations timeout (in seconds, default: default timeout)

* **-r RETRIES** retry attempts for each operation (default: no retries)

* **-d SEC** delay between virtual port operations (default: 20ms)

* **-y** save ModBus port config after creation

* **ID** virtual port ID which will be used later in :doc:`PHI</drivers>`
  configurations

* **PARAMS** ModBus params

ModBus params should contain the configuration of hardware ModBus port. The
following hardware port types are supported:

* **tcp** , **udp** ModBus protocol implementations for TCP/IP networks. The
  params should be specified as: *<protocol>:<host>[:port]*, e.g.
  *tcp:192.168.11.11:502*

* **rtu**, **ascii**, **binary** ModBus protocol implementations for the local
  bus connected with USB or serial port. The params should be specified as:
  *<protocol>:<device>:<speed>:<data>:<parity>:<stop>* e.g.
  *rtu:/dev/ttyS0:9600:8:E:1*

As soon as the port is created, it can be used by PHI. Let's create ModBus TCP
port and load **dae_ro16_modbus** PHI module:

.. code-block:: bash

    eva uc modbus create p1 tcp:192.168.11.11:502 -y
    eva uc phi load r1 dae_ro16_modbus -c port=p1,unit=1 -y

As the result, controller creates a :doc:`driver</drivers>` *r1.default*
which can be set to :doc:`item</items>` to work with any relay port of unit #1
of the ModBus relay 192.168.11.11 connected via TCP.

.. warning::

    UC will grant ModBus port access to PHI only if it has enough timeout to
    wait for the longest possible call. It means operation timeout
    (**action_timeout**, **update_timeout**) in :doc:`item</items>` should be
    greater than *modbus_port_timeout*(1+modbus_port_retries)*. If the
    command max timeout is less than this value, attempts to access ModBus
    virtual port return an error.

If you need to change ModBus port params or options, you can always create new
ModBus virtual port with the same ID, without deleting the previous one. Port
configuration and options will be overwritten.

Testing ModBus virtual port
===========================

To test defined ModBus virtual port, execute the following command:

.. code-block:: bash

    eva uc modbus test <ID>
    # e.g.
    eva uc modbus test p1

The command connects UC to ModBus port and checks the operation status.

.. note::

    As ModBus UDP doesn't require a port to be connected, **test** command
    always return "OK" result.

Deleting ModBus virtual port
============================

To delete ModBus virtual port, execute the command:

.. code-block:: bash

    eva uc modbus destroy <ID>
    # e.g.
    eva uc modbus destroy p1

Note that controller doesn't check if the port is in use or not, so double
check this manually before deleting it.

.. _modbus_slave:

ModBus slave
============

:doc:`/uc/uc` can work as ModBus slave. Ports, the slave listens to, are set in
*etc/uc.ini*. ModBus over TCP, UDP and serial ports (rtu/ascii/binary) is
supported.

Controller uses single memory space for all ports it listens to, ports can have
different ModBus addresses. Memory space has 10 000 holding registers, 10 000
coils, 10 000 input registers and 10 000 discrete inputs.

:ref:`Units<unit>` can listen to memory space changes and automatically update
their *status* and *value* as soon as ModBus register is being changed. To
activate state updates via ModBus slave memory space, set unit
**modbus_status** and/or **modbus_value** properties to the corresponding
registers, using before the number **c** for coil and **h** for holding
register, e.g. *c5* for 5th coil register, *h50* for 50th holding register etc.

:ref:`Sensors<sensor>` can update their *value* only. Don't forget to enable
sensor (set its status to 1) manually.

More complex data processing can be performed via :ref:`PHI<phi>` modules.

