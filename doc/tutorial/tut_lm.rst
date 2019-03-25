Logic Manager configuration
***************************

* EVA Tutorial parts

  * :doc:`Intro<tutorial>`
  * :doc:`tut_uc`
  * **Logic Manager configuration** << we are here
  * :doc:`tut_sfa`
  * :doc:`tut_ui`

So, let us proceed with our configuration. As soon as :doc:`/uc/uc` is
already configured, let us move on with :doc:`/lm/lm`.

.. contents::

Configuring notification system and API key for SFA
===================================================

.. include:: skip_easy.rst

The first step is to connect the server to the local :ref:`MQTT<mqtt_>` to
allow Logic Manager to receive UC item states in real time:

.. code-block:: bash

    lm-notifier create eva_1 mqtt:eva:secret@localhost -s plant1 -y

then subscribe the notification system to receive the states of the local
:ref:`logic variables<lvar>` which will be created later:

.. code-block:: bash

    lm-notifier subscribe state eva_1 -v lvar -g '#'
    lm-notifier config eva_1

.. code-block:: json

    {
        "enabled": true,
        "events": [
            {
                "groups": [
                    "#"
                ],
                "subject": "state",
                "types": [
                    "#"
                ]
            }
        ],
        "host": "localhost",
        "id": "eva_1",
        "password": "secret",
        "space": "plant1",
        "type": "mqtt",
        "username": "eva"
    }

Add :ref:`API key<lm_apikey>` for :doc:`/sfa/sfa` in **etc/lm_apikeys.ini**:

.. code-block:: ini

    [sfa]
    key = secret_for_sfa2
    groups = #
    hosts_allow = 127.0.0.1

Restart LM PLC:

.. code-block:: bash

    ./sbin/lm-control restart

Connecting UC controller
========================

.. include:: skip_easy.rst

Connect the local :doc:`UC</uc/uc>` to :doc:`/lm/lm` using the key we've
created in **etc/uc_apikeys.ini** in the :doc:`previous part<tut_uc>` of the
tutorial:

.. code-block:: bash

    lm-cmd controller append http://localhost:8812 -a secret_for_lm -m eva_1 -y
    lm-cmd -J remote -p S

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

Looks correct, sensors are loaded, let's check the units:

.. code-block:: bash

    lm-cmd -J remote -p U

Let LM PLC reload the items from the connected controller every 60 seconds, if
new ones are added in future:

.. code-block:: bash

    lm-cmd controller set uc1 reload_interval 60 -y

Building logic
==============

We have two tasks: to switch on the inside ventilation if the temperature is
above 25 degrees, and handle the events received from the motion sensor. Do not
forget that the inside ventilation should be off from 9pm till 7am. Though this
will be later implemented via **sfa-cmd** and system **cron**, we should get
it prepared now.

Ventilation logic
-----------------

We chose our example, as far as the boundary conditions of the sensor is a very
common problem for such tasks.

If we solve this problem by creating the following two rules:

* if the temperature is above 25 degrees, the fan is switched on
* if below - switched off

the following problem may occur: if the temperature will hover around 25
degrees, the ventilation system will constantly switch on and off. Therefore, a
breakdown is highly possible. We cannot simply set up **chillout_time** in the
:doc:`rule</lm/decision_matrix>`, it completely disables the rule, so it
doesn't match after the chillout is over, if both previous and current state
are in the range.

Due to the flexibility of EVA there is a number of solutions of this problem:

**Option 1:**

Ventilation is switched on, if the temperature is above 25 degrees, and
switched off if it is below e.g. 25.5. The logic will have half a degree gap
for the equipment not to be overloaded. If the temperature changes not that
quickly, this option would be the best one.

**Option 2:**

* Create the rule without a condition activated whenever the env/temp1 sensor
  changes its value

* The stop-start logic, as well as the temperature monitoring logic, is fully
  transferred to the :doc:`macro</lm/macros>` executed by the above rule.

* macro reads the value of :ref:`lvar<lvar>` **ventilation/start_temp** (to
  avoid hardcoding *25* in a macro code and let it have an ability to be
  changed from outside)

* To avoid the continuous running of macro, use the rule prop
  **chillout_time**. Or even

* Use :ref:`unit_status<macro_api_unit_status>` macro function to get the
  current ventilation status and use macro :ref:`lock<macro_api_lock>` function
  to block its changing too often e.g. for 5 minutes

The macro code will look like:

.. code-block:: python

    if status('unit:ventilation/vi') and \
        value('sensor:env/temp1') < value('ventilation/start_temp'):
      try: lock('ventilation/vi/control', 5, 300)
      except: exit()
      stop('ventilation/vi')
    elif not status('unit:ventilation/vi') and \
        value('sensor:env/temp1') >= value('ventilation/start_temp'):
      try: lock('ventilation/vi/control', 5, 300)
      except: exit()
      start('ventilation/vi')

**Option 3**

Increase **update_interval** prop of **env/temp1** :ref:`sensor<sensor>` e.g.
to 300 seconds. This option will work, though it is not that good because the
system will obtain the current temperature with a 5 min delay (or we need to
duplicate the sensor in :doc:`UC</uc/uc>` and create a quicker one).

**Option 4**

Add a 5 minutes delay at the end of **xc/uc/vi** action script, allow **vi**
queues (set **action_queue=1** unit prop), and start ventilation from the macro
in the following way:

.. code-block:: python

    try: lock('ventilation-example3', 5, 10)
    except: exit()
    # clean up all queued action
    q_clean('ventilation/vi') 
    # exec our action
    start('ventilation/vi') 
    unlock('ventilation-example3')

Not bad, but we loose an ability to exec the :ref:`actions<ucapi_action>` with
**w** param and get the correct completion status.

**Option 5**

Use system crontab to copy **env/temp1** value to some :ref:`logic
variable<lvar>` every 5 minutes. Then work only with this logic variable. This
option is too awkward, the logic of the system crontabs will sooner or later
turn into the script hell. Therefore, we will use cron only for the time
schedule-based logic, everything else will be done using EVA.

**Option 6 - the best one**

There are more than 10 options to solve our problem, but we will choose the
best one: delayed start. Moreover, we have a condition to run ventilation only
in 5 minutes after the temperature becomes >=25. So, we will use this option.
The other ones have been reviewed just because this is a tutorial.

Create two :ref:`logic variables<lvar>`:

.. code-block:: bash

    lm-cmd create lvar:ventilation/vi_auto -y
    lm-cmd create lvar:ventilation/vi_timer -y
    lm-cmd set vi_auto -s 1 -v 1

The first one will act as a flag for the ventilation control
:doc:`macro</lm/macros>`: if the flag is on 1, the control is possible, if
off - the ventilation should not be touched. The second variable will act as a
delayed start timer.

Create a control macro which satisfies for our current task and the scheduled
ventilation switching. We will give it two parameters: the first - what to do
with ventilation (0 - switch off, 1 - switch on), the second - who runs it:
temperature :doc:`event</lm/decision_matrix>`, our delayed start timer or a
system cron:

.. code-block:: bash

    lm-cmd macro create control/vi_control -y

Put a macro code in **xc/lm/vi_control.py** file

.. code-block:: python

    if _1: # if anyone asks to switch on the ventilation
        if _2 == 'event': # if it's an event
        reset('ventilation/vi_timer') # reset delayed start timer
        elif _2 == 'timer': # if it's a timer
            if value('ventilation/vi_auto'):
                start('ventilation/vi') # start ventilation if allowed
        elif _2 == 'cron': # if it's a system cron
            # disable the ventilation automation for everyone but cron
            clear('ventilation/vi_auto', 0):
            start('ventilation/vi') # start ventilation
    else: # if it's a command to switch off
        clear('ventilation/vi_timer') # stop the delayed start timer
        if value('ventilation/vi_auto') or _2 == 'cron':
            # in case the command is send by cron or
            # if allowed to stop - stop it
            stop('ventilation/vi') 
        if _2 == 'cron':
            # if the ventilation is switched off by cron
            # then enable automation back for everyone
            set('ventilation/vi_auto', 1) 

The macro requires 3 :doc:`rules</lm/decision_matrix>`:

The first one will match if the temperature is above or equal to 25 degrees and
activates the delayed start timer:

.. code-block:: bash

    lm-rules add -E -y -x value --type sensor --group env --item temp1 --ge 25 --initial any -m vi_control -a "1 event"

The second one will match if the temperature is below 25 degrees and switches
the ventilation off (if it's allowed):

.. code-block:: bash

    lm-rules add -E -y -x value --type sensor --group env --item temp1 --lt 25 --initial any -m vi_control -a "0 event"

The third rule will run the macro to turn the ventilation on as soon as the
delayed start timer finishes the countdown:

.. code-block:: bash

    lm-rules add -E -y --type lvar --group ventilation --item vi_timer --exp -m vi_control -a "1 timer"

Motion sensor logic
-------------------

We will need one variable identifying whether the alarm is switched on or not:

.. code-block:: bash

    lm-cmd create lvar:security/alarm_enabled -y
    lm-cmd set alarm_enabled -s 1 -v 0

Additionally, we will need two macros. The first one will send API call to
alarm system:

.. code-block:: bash

    lm-cmd macro create security/alarm_start -y

put its code to **xc/lm/alarm_start.py**:

.. code-block:: python

    # do not send API calls more than once in 30 minutes
    try: lock('alarm-start', expires = 1800) 
    except: exit()
    # call the alarm system API
    get('http://alarmserver/api/activate?apikey=blahblahblah')

The second one will check whether the alarm is switched, to either switch on the
alarm system or just turn on the lighting:

.. code-block:: bash

    lm-cmd macro create security/motion1_handler -y

put its code to **xc/lm/motion1_handler.py**:

.. code-block:: python

    if value('security/alarm_enabled'):
        run('security/alarm_start')
    else:
        start('light/lamp1')

Plus the additional rule executing **motion1_handler** macro when the motion
sensor detects an activity:

.. code-block:: bash

    lm-rules add -E -y -x value --type sensor --group security --item motion1
    --eq 1 -m motion1_handler

The logic is set up. We can review and test it in :doc:`/lm/lm_ei` and
configure :doc:`tut_sfa` to interact with the external applications (in our
case - the system cron, for the scheduled ventilation control) and serve the
system web interface.
