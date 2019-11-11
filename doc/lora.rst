LoRa
****

:doc:`/uc/uc` can act as `LoRa <https://en.wikipedia.org/wiki/LoRa>`_ network
server.

.. figure:: lorawan.png
   :scale: 100%
   :alt: LoRa network

Before loading :doc:`drivers </drivers>` for LoRa equipment, LoRa support must
be enabled *etc/uc.ini* configuration file: you should uncomment/change
*listen* and *hosts_allow* options in **[lora]** section.

After :doc:`/uc/uc` restart (*eva uc server restart*), loaded LoRa PHIs
immediately start receiving packets from the equipment.

.. note::

   Only LoRa protocol version 2 (1.0.2+) is supported.
