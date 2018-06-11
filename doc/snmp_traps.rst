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

set_down - handling the failures
--------------------------------

When the controller receives the trap notification indicating that the item is
not available or disabled, its status is set to -1.

This can be made with **set_down** variable, which's set similarly to
**ident_vars**. If there are several OID, they should be listed and separated
by a commas when setting up. The handler assigns an error status to the item
only if all set_down variables match the trap. 

Example:

.. code-block:: bash

    uc-cmd set_prop -i unit1 -p snmp_trap.set_down -v 1.3.6.1.4.1.3855.1.7.9.0=7

Result:

.. code-block:: bash

    uc-cmd list_props -i unit1

.. code-block:: json

    {
    "snmp_trap": {
       "set_down": {
           "1.3.6.1.4.1.3855.1.7.9.0": "7"
       }
    }

To reset **set_down** variable, run the command without -v key. 

set_status - setting the item status
------------------------------------

If the source device sends the trap notifications with the variable having the
item status in the format similar to EVA, the handler can immediately change
the status to the assigned one. Each item can have only one **set_status**
variable containing OID where item status is being set in a trap.

Example:

.. code-block:: bash

    uc-cmd set_prop -i unit1 -p snmp_trap.set_status -v 1.3.6.1.4.1.3855.1.7.17.1

Result:

.. code-block:: bash

    uc-cmd list_props -i unit1

.. code-block:: json

    {
    "snmp_trap": {
       "set_status": "1.3.6.1.4.1.3855.1.7.17.1"
       }
    }

To reset **set_status** variable, run the command without -v key. 

set_value - setting the item value
----------------------------------

If the source device sends the trap notifications with the variable having the
item value  (usually, these are various sensor controllers which i.e. send the
current temperature every minute), the handler can immediately change the
value to the assigned one. Each item can have only one **set_value**
variable containing OID where item vlue is being set in a trap.

Example:

.. code-block:: bash

    uc-cmd set_prop -i unit1 -p snmp_trap.set_status -v 1.3.6.1.4.1.3855.1.7.17.2

Result:

.. code-block:: bash

    uc-cmd list_props -i unit1

.. code-block:: json

    {
    "snmp_trap": {
       "set_value": "1.3.6.1.4.1.3855.1.7.17.2"
       }
    }

To reset **set_value** variable, run the command without -v key. 

set_if - conditional state updates
----------------------------------

If the received trap notification contains certain variables but none of them
can be used to set status and/or value as-is, you can define own rules and set
the item status/value according to them.

This operates similary to **set_down**, the only difference is that
**set_down** sets the item status to -1, while **set_if** allows you to set the
status and/or value on your own.

The variable is set as follows:

    status,value:OID=val1,OID2=val2,OID3=val3

If you don't need to set status or value, set it to null when defining.

For example, let's add two conditions: 

.. code-block:: bash

    uc-cmd set_prop -i unit1 -p snmp_trap.set_if -v 1,null:1.3.6.1.4.1.3855.1.7.1.0=4
    uc-cmd set_prop -i unit1 -p snmp_trap.set_if -v null,10:1.3.6.1.4.1.3855.1.7.1.0=2

Result:

.. code-block:: bash

    uc-cmd list_props -i unit1

.. code-block:: json

    {
    "snmp_trap": {
        "set_if": [
            {
                   "value": "10",
                   "vars": {
                       "1.3.6.1.4.1.3855.1.7.1.0": "2"
                    }
            },
            {
                "status": 1,
                "vars": {
                    "1.3.6.1.4.1.3855.1.7.1.0": "4"
                }
            }]
        }
    }

When the controller receives a trap with OID *1.3.6.1.4.1.3855.1.7.1.0=2*, the
value of the item is set to 10. When OID *1.3.6.1.4.1.3855.1.7.1.0=4*, the
status is set to 1.

One item can have multiple **set_if** conditions but they can only be added. You
can delete the condition only by deleting the entire **set_if** variable by
running the command without -v key.

Disabling SNMP traps processing
-------------------------------

To disable SNMP traps processing for a single item, delete its **snmp_traps**
variable:

.. code-block:: bash

    uc-cmd set_prop -i unit1 -p snmp_trap

