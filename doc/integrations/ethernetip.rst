Ethernet/IP
***********

Drivers
=======

EVA ICS provides two generic universal PHI modules for Ethernet/IP devices:
*enip_sensor* and *enip_xvunit*. The modules are easy to integrate and provide
basic support of Ethernet/IP-enabled devices.

Logic
=====

EVA ICS :ref:`sensors<sensor>` have "values" and item "status" is used only as
an error indicator. En/IP tags can be mapped to sensor values as-is with
*enip_sensor* PHI module.

EVA ICS :ref:`units<unit>` have both "status" and "value" fields, which form a
complete item state. So En/IP tag mapping logic is a little bit more
complicated:

* If En/IP tag (integer) should be mapped to unit status (ON/OFF/other modes),
  it's mapped to unit status with *enip_xvunit* PHI module as-is.

* If En/IP tag is used as an operation mode, it can be mapped to unit value
  with additional *enip_xvunit* instance, loaded with *xv=true* configuration
  param. Status of the unit, assigned to driver with such PHI module can be
  either 1 (OK) or -1 (ERROR), tag value is mapped to unit value as-is. Such
  units don't perform "toggle" actions, general actions should be executed with
  *status=1* and *value=<DESIRED_TAG_VALUE>*

The above logic is used only for generic *enip_sensor* and *enip_xvunit*
modules. Other modules may have different logic mapping, depending on connected
equipment and tasks.

Setup
=====

Required libraries
------------------

Both PHI modules require `cpppo <https://github.com/pjkundert/cpppo/>`_ Python
library. The library isn't installed by default. Set *EXTRA="cpppo==4.0.6"* in
*/opt/eva/etc/venv* and rebuild EVA ICS venv (*/opt/eva/install/build-venv*).

Downloading PHIs
----------------

.. code:: bash

    eva uc phi download https://get.eva-ics.com/phi/enip/enip_sensor.py
    eva uc phi download https://get.eva-ics.com/phi/enip/enip_xvunit.py


Creating tag lists
------------------

If bulk updates are planned, both PHIs require tag lists - lists of CIP tags to
poll from/to the En/IP equipment. Tag lists are simple text files, with one tag
per line. If tag contains an array, element index should be specified.

If bulk updates are not required or performed with :doc:`data
pullers</datapullers>`, the tag lists are not required.

.. code::

    TAG1
    TAG2
    TAG3[0]

If setting tags is planned (working with *enip_xvunit*), it's highly recommended to set variable types, at least for the integer tags:

.. code::

    TAG1:UINT
    TAG2:UINT
    TAG3[0]:SINT

Valid types are: *REAL, SINT, USINT, INT, UINT, DINT, UDINT, BOOL, WORD, DWORD, IPADDR, STRING,
SSTRING*.

Another way is to specify "_type" driver configuration variable, while
assigning the driver to items.

Configuring
-----------

Both modules support *update* param, which allows to pull tags from the
equipment with a single request and update all assigned EVA ICS items.

Let's load PHI for sensors:

.. code:: bash

    eva uc phi load es1 enip_sensor -c host=HOST_OR_IP_OF_EQUIPMENT,taglist=/PATH/TO/TAGLIST,update=1 --save

    # create a couple of sensors

    eva uc create sensor:tests/test1 --enable --save
    eva uc create sensor:tests/test2 --enable --save

    # assign driver to sensors
    eva uc driver assign sensor:tests/test1 es1.default -c port=TEST1_TAG --save
    eva uc driver assign sensor:tests/test2 es1.default -c port=TEST2_TAG --save

    # trigger the first sensor state update. all other updates will be received
    # automatically, every second

    eva uc update sensor:tests/test1
    eva uc update sensor:tests/test2
