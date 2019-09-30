Item scripts
************

Item scripts are used to update :doc:`items'<items>` state and execute actions.
Scripts are placed in xc folder (**xc/uc** for :doc:`/uc/uc`, **xc/lm** for
:doc:`/lm/lm`) and may be either written in any scripting language or be binary
executables. The script file should have exec permissions.

:doc:`/uc/uc` has 2 ways for controlling and monitoring items:
:doc:`drivers</drivers>` and item scripts. Sometimes item scripts are harder to
implement as you must define all logic by yourself, as well as implement
hardware calls, they are also slower because controller needs to execute an
external process. But item scripts are more reliable than drivers because the
external process can be easily terminated/killed by timeout, so if you don't
have a driver for your equipment or the driver is unstable, it is a good idea
to use scripts.

All the examples provided in this documentation are written in the classic
Bourne shell (bash). It is recommended to use dash or perl in heavy loaded
production systems to provide better startup speed. Experience has shown that
the modern systems do not require the use of the lower-level languages compiled
into executable files: it complicates integration and servicing; on the
other hand, the difference in program operation is only a few milliseconds.

The script always has max execution time (timeout) specified in item
configuration (or default controller timeout). After that the system terminates
the script operation: firstly - voluntary, by sending SIGTERM, then - forcibly
by sending SIGKILL (this in-between time may be changed in item configuration
with param *term_kill_interval*)

Script or program always gets the environment variables:

* all variables from the controller var file (:ref:`uc_cvars<uc_cvars>` or
  :ref:`lm_cvars<lm_cvars>`)
* **PATH** variable with additional EVA bin and xbin subfolders
* **EVA_ITEM_ID** item ID which the script is executed for
* **EVA_ITEM_OID** item OID (**type:group/id**)
* **EVA_ITEM_TYPE** item type: unit, sensor or lvar, (lvars can also be
  updated with scripts)
* **EVA_ITEM_GROUP** full item group
* **EVA_ITEM_PARENT_GROUP** the nearest parent group of the item (e.g.
  building1/env/room1/temp1 - room1)
* **EVA_ITEM_FULL_ID** full item ID
* **EVA_ITEM_STATUS** current item status
* **EVA_ITEM_VALUE** current item state value

The system considers the script to be successful if its exit code is 0.

Item actions
------------

Item actions are used to control the units. After the :ref:`unit<unit>` action
has been called, the controller executes the appropriate script. By default,
control scripts are placed in xc/uc/ folder and named ID, where ID is a unit
ID, for example, xc/uc/lamp1. This may be changed in the item configuration to
let e.g. one script execute actions for a group of units.

The startup parameters of the action script include:

* **param1** unit ID
* **param2** new unit status
* **param3** new unit value

.. note::

    If unit action is called without value, action control script is called
    with previous known unit value

A simple example script: send toe command to `X10
<https://en.wikipedia.org/wiki/X10>`_ controller via `mochad
<https://sourceforge.net/projects/mochad/>`_

.. code-block:: bash

    #!/bin/sh
    [ $2 -eq 0 ] && CMD="off" || CMD="on"
    echo "pl $1 $CMD" | nc localhost 1099

Such script is actually universal for X10 (in case units are named according to
X10 - a1-aX)

Another example: activate the third `EG-PM2-LAN
<http://energenie.com/item.aspx?id=7557>`_ plug. Here we access EG1_IP variable
from :ref:`uc_cvars<uc_cvars>`

.. code-block:: bash

    #!/bin/sh
     
    EG-PM2-LAN $EG1_IP 3 $2

Another example: control the relay (4 modules, 1 relay block) by `Denkovi
AE <http://denkovi.com/relay-boards>`_

.. code-block:: bash

    #!/bin/sh
    
    ${RELAY1_CMD}.1.4.0 i $2

where in :ref:`uc_cvars<uc_cvars>`:

.. code-block:: bash

    RELAY1_CMD = snmpset -v1 -c private RELAY_IP_ADDRESS .1.3.6.1.4.1.19865.1.2

In the previous examples, we used the same command for turning the units
on/off. Let us review a more complex logic. The next example shows how EVA can
shut down the remote server machine and turn it on via Wake on LAN (tip: such
script requires more action_timeout in unit config):

.. code-block:: bash

    #!/bin/sh
    
    case $2 in
    0)
      ssh eva@${SERVER_IP} "sudo /sbin/poweroff"
       ;;
    1)
      wakeonlan ${SERVER_MAC}
       ;;
    esac

In the :ref:`queue<uc_queues>` history script is marked as completed if it
completed independently with 0 code, failed - if the code differs from 0.

The script or program can display anything on stdout/stderr. This data, as well
as the exit code, will be recorded in "out" and "err" fields of the
:ref:`result<ucapi_result>` dict.

Sometimes it is useful to catch SIGTERM in the script/program, e.g. if you
operate a motor that must be stopped after the script gets a termination
signal. Warning:, the system does not track/stop child processes executed after
SIGTERM is sent to the script.

Passive updates of item state
=============================

Passive updates are used to collect the state of the equipment which doesn't
report its state by itself. By default, scripts for passive updating of item
state are named **ID_update**, where ID is a item ID, for example:
*lamp1_update*.

The status update script is executed:

* Every X seconds, if *update_interval* specified in the config is more than 0
* After the :ref:`unit<unit>` action succeeds (if
  *update_exec_after_action=true* in config)

The system considers the script was executed successfully if its exit code is
0, otherwise, its new item state is ignored.

Passive update scripts get the following parameters:

* **param1** item ID
* **param2** "update"

Script should print on stdout only the new status and (optionally) value,
separated by space, e.g.

    0 NEW_VALUE

For the sensor, its data should be printed as:

    1 VALUE

where 1 means the sensor is working properly.

Let us analyze an example of a simple script, e. g. state update of the sensor
that monitors the remote machine

.. code-block:: bash

    #!/bin/sh
    
    ping -W1 -c1 ${SERVER_IP} > /dev/null 2>&1 && echo "1 1"||echo "1 0"

Unit status - the third `EG-PM2-LAN <http://energenie.com/item.aspx?id=7557>`_
plug

.. code-block:: bash

    #!/bin/sh

    EG-PM2-LAN evacc-rl5|cut -d, -f3

Update state of the relay (4 modules, 1 relay block) by `Denkovi
AE <http://denkovi.com/relay-boards>`_

.. code-block:: bash

    #!/bin/sh

    ${RELAY1_UPDATE_CMD}.2.0|awk -F\  '{ print $4 }'

where in :ref:`uc_cvars<uc_cvars>`:

.. code-block:: bash

    RELAY1_UPDATE_CMD = snmpget -v2c -c public RELAY_IP_ADDRESS .1.3.6.1.4.1.42505.6.2.3.1.3

Multiupdate scripts
===================

:ref:`Multiupdates<multiupdate>` allow updating the state of several items with
one script which works like a normal passive update script and outputs the
states of the monitored items line-by-line:

.. code-block:: bash

    item1_status item1_value
    item2_status item2_value
    .....

The order of the output should correspond to the order of the items in the
multiupdate.

By default, multiupdate scripts are named **ID_update**, where ID is a
multiupdate ID, for example, *xc/uc/temperatures_update* for mu ID =
temperatures.

For example, let's update all 8 units connected to the relay controlled by
`DS2408 <https://datasheets.maximintegrated.com/en/ds/DS2408.pdf>`_

.. code-block:: bash

    #!/bin/sh

    w1_ds2408 28-999999999999 || exit 1

The script output will be as approximately follows:

.. code-block:: bash

    1
    0
    1
    1
    1
    1
    0
    1

where each row contains the status of the unit connected to the corresponding
relay port.

.. _cmd:

Commands
========

Commands are used if you need to run some commands remotely on the server where
EVA controller is installed. Commands are executed with :doc:`controller cli
tools</cli>`, with SYS API function :`ref`:`cmd<cmd>` or with :ref:`macro
function<macro_api_cmd>`.

For command scripts:

* Configurations are absent. Scripts are named as **xc/cmd/SCRIPT_NAME**
* Script timeout is set when it is started

Example of a command usage: a speaker is connected to a remote machine. We
want to play some sound as an additional feedback after the certain macros or
actions are executed

**xc/cmd/play_snd**

.. code-block:: bash

    #!/bin/sh

    GAIN=-7

    killall play > /dev/null 2>&1 && killall -9 play > /dev/null 2>&1
    play /data/snd/$1.wav gain ${GAIN}

when you call the command, the sound file_name will be played. If you want to
wait until the playback is over add w=15 to API call i.e. to wait 15 seconds
before continuing.

