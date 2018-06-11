SNMP traps
==========

Active :doc:`item<items>` updates can be done using SNMP traps notifications.

Usually each automation device sends SNMP traps in its specific format and the
data should be parsed individually for subsequent processing. You can use a
third-party server to receive traps, for example, `snmptrapd
<http://net-snmp.sourceforge.net/docs/man/snmptrapd.html>`_ or trap handler
included in EVA :doc:`/uc/uc`.

Built-in trap handler should be enabled in :ref:`UC configuration
file<uc_ini>`. Usually, SNMP traps server listen on the port 162. The embedded
SNMP traps handler can work with SNMP v1 and SNMP v2c protocols.

Both :ref:`units<unit>` and :ref:`sensors<sensor>` can update its state through
SNMP traps processing. After the item configuration param **snmp_trap** is set
up, it automatically subscribes to the incoming notifications and accept only
the relevant ones. 

Currently EVA works with SNMP OIDs only - all snmp variables should be created
in this format. To change **snmp_trap** variable and its child elements you may
use *uc-cmd* :doc:`console app</cli>` or UC API :ref:`set_prop<uc_set_prop>`
function. In this tutorial we'll configure SNMP-traps handler with *uc-cmd*. 

ident_vars - identifying the trap
---------------------------------

**snmp_trap.ident_vars** variable is used by the handler to filter the trap
notifications and parse only those ones directly related to the item. You
should use it if, for example, the source sends the state change notifications
with the same OID for different items, but the trap contains some tokens or
item IDs identifying that the notification is addressed to the particular item.
You can set several ident vars (separated by a comma) at once. The notification
will be processed only if all **ident_vars** match the trap.

Example:

.. code-block:: bash

    uc-cmd set_prop -i unit1 -p snmp_trap.ident_vars -v 1.3.6.1.4.1.3856.1.7.11.0=14,1.3.6.1.4.1.3856.1.7.11.1=U1

Result:

.. code-block:: bash

    uc-cmd list_props -i unit1

.. code-block:: json

    {
    "snmp_trap": {
           "ident_vars": {
               "1.3.6.1.4.1.3856.1.7.11.0": "14",
               "1.3.6.1.4.1.3856.1.7.11.0": "U1"
           },
        }
    }

To reset **ident_vars** variable, run the command without -v key.
