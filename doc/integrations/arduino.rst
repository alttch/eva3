Arduino
*******

You may connect Arduino or similar boards to :doc:`/uc/uc` to handle events
from connected sensors or receive commands for locally connected relays, motors
etc.

Receiving commands from EVA ICS
===============================

There's no common way controlling embedded boards from EVA ICS. You may define
any API inside a board, then just use :doc:`external scripts</item_scripts>` or
:doc:`develop own PHI module </phi_development>` to link :doc:`/uc/uc` and
board.

Sending data to EVA ICS UC
==========================

It's highly recommended to use :doc:`/uc/uc_udp_api` to communicate with
:doc:`/uc/uc` to avoid Arduino board freezing.

To enable UDP API, you must firstly configure *listen* and *hosts_allow*
options in *etc/uc.ini* (don't forget to restart :doc:`/uc/uc` after
configuration is modified).

Example. Consider there are 2 motion (PIR) sensors connected with Arduino board
on pins #2 and #3, the board has Ethernet shield to send events via UDP
protocol, there is also a signal LED connected to board pin #7.

On events, the board updates states of EVA ICS sensors
*sensor:security/motion1* and *sensor:security/motion2*. We'll use plain
(unencrypted) UDP API and :doc:`/uc/uc` will receive state updates without API
key.

.. literalinclude:: ../code-examples/arduino-alarm-example.ino
   :language: c
