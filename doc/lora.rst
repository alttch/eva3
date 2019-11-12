LoRa
****

:doc:`/uc/uc` can act as `LoRaWAN <https://en.wikipedia.org/wiki/LoRa>`_
network server.

.. figure:: lorawan.png
   :scale: 100%
   :alt: LoRa network

Before loading :doc:`drivers </drivers>` for LoRa equipment, LoRaWAN support
must be enabled *etc/uc.ini* configuration file: you should uncomment/change
*listen* and *hosts_allow* options in **[lorawan]** section.

After :doc:`/uc/uc` restart (*eva uc server restart*), loaded LoRa PHIs
immediately start receiving packets from the gateways.

.. note::

   Currently EVA ICS supports only LoRa legacy Semtech UDP protocol version 2.
