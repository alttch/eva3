SCADA Final Aggregator configuration
************************************

* EVA Tutorial parts

  * :doc:`Intro<tutorial>`
  * :doc:`tut_uc`
  * :doc:`tut_lm`
  * **SCADA Final Aggregator configuration** << we are here
  * :doc:`tut_ui`

So, let us proceed with our configuration. :doc:`/uc/uc` has already been set
up and :doc:`/lm/lm` as well. Therefore, let us move on to :doc:`/sfa/sfa`
configuration.

Since the logic has already been implemented, we have only two tasks: to
interconnect all the controllers and connect the system cron that will control
the ventilation schedule.

.. contents::

Notification system configuration
=================================

.. include:: skip_easy.rst

The first step is to connect the server to the local :ref:`MQTT<mqtt_>` to
allow :doc:`/sfa/sfa` to get the state of :doc:`UC</uc/uc>` and :doc:`LM
PLC</lm/lm>` :doc:`items</items>` in real time:

.. code-block:: bash

    eva ns sfa create eva_1 mqtt:eva:secret@localhost -s plant1 -y

We won't subscribe the notifier to anything, because all the data are received
from it, and there is nothing to send instead.

.. code-block:: bash

    eva ns sfa config eva_1 

.. code-block:: json

    {
        "enabled": true,
        "host": "localhost",
         "id": "eva_1",
        "password": "secret",
        "space": "plant1",
        "type": "mqtt",
        "username": "eva"
    }

Restart SFA:

.. code-block:: bash

    ./sbin/sfa-control restart

Connecting controllers
======================

.. include:: skip_easy.rst

The next step is to connect the local :doc:`UC</uc/uc>` and :doc:`LM
PLC</lm/lm>` to :doc:`/sfa/sfa` with the keys created specifically for SFA:

.. code-block:: bash

    eva sfa controller append http://localhost:8812 -a secret_for_sfa -m eva_1 -y
    eva sfa controller append http://localhost:8817 -a secret_for_sfa2 -m eva_1 -y

.. code-block:: bash

    eva sfa -J remote -p S

.. code-block:: json

    [
        {
            "controller_id": "uc/uc1",
            "group": "security",
            "id": "motion1",
            "oid": "sensor:security/motion1",
            "status": 1,
            "type": "sensor",
            "value": "0"
        },
        {
            "controller_id": "uc/uc1",
            "group": "env",
            "id": "temp1",
            "oid": "sensor:env/temp1",
            "status": 1,
            "type": "sensor",
            "value": "25.4"
        }
    ]

Looks fine, :ref:`sensors<sensor>` are loaded, let's check :ref:`units<unit>`
and :ref:`logic variables<lvar>`:

.. code-block:: bash

    eva sfa -J remote -p U
    eva sfa -J remote -p LV

Let SFA reload the items from the connected controllers every 60 seconds, if
new ones are added in future:

.. code-block:: bash

    eva sfa controller set uc/uc1 reload_interval 60 -y
    eva sfa controller set lm/lm1 reload_interval 60 -y


Connecting external applications
================================

There is only one external application - system cron. We won't connect it via
SFA API, but simply by running **eva sfa** (*sfa-cmd*) :doc:`console
application</cli>`.

We provide this example for one reason: you should always connect your external
applications to :doc:`SFA</sfa/sfa>` only. Controllers may be changed and,
therefore, the setup may be extended: for example, one :doc:`/lm/lm` may be
replaced by the three ones installed on the different servers. However, the
local SFA will never be changed. All you need is to connect new controllers to
it, and EVA item infrastructure will be available again by its usual ID.

The next step it to connect cron for it to run ventilation control macro (edit
/etc/crontab or user's crontab):

.. code-block:: bash

    0 7 * * *    root   /path/to/sfa-cmd macro run control/vi_control -a "0 cron"
    0 21 * * *    root   /path/to/sfa-cmd macro run control/vi_control -a "1 cron"

As you can see, there is no rocket science here. :doc:`/sfa/sfa` is configured
by a few commands and immediately starts collecting the data and events. In
turn, it will save you a lot of time by structuring your setup. Now let's
create :doc:`SFA Framework interface<tut_ui>` that will be served by SFA.
