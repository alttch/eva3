FAQ
===

.. contents::

Is this a "smart home"?
-----------------------

EVA is a universal system used for the construction of both "smart home" and
automated control system (`ICS
<https://en.wikipedia.org/wiki/Industrial_control_system>`_) on the industrial
enterprise.

In fact, most products positioning themselves as "smart home" are just a dumb
control panels with a web interface. Moving light switch from the wall to the
screen doesn't make it "smart". In turn, our system is equipped with a powerful
and constantly evolving :doc:`/lm/lm` for the automatic
:doc:`decision-making</lm/decision_matrix>`.

Is this IoT?
------------

In a way, yes. As far as `IoT
<https://en.wikipedia.org/wiki/Internet_of_things>`_ is a part of the
automation process, we are the part of IoT, in turn. However, from the
thoursands of components positioning themselves as "IoT", we choose only those
ones working:

* Reliably
* Safely
* Autonomously

And, most preferably, having an open API to be connected to any system.

The classic situation typical for IoT market involves controlling your device
via the Internet with the help of software on the developer servers (aka
"clouds"). As you can see it is:

* Unreliable
* Dangerous
* Not autonomous

Moreover, you can't seriously use it even at home. Our system doesn't require
registration, we don't need your phone number, email or home address - just
download, install and use it. The system works only for you and sends data to
no one but you. The code is fully open, so that you can control everything
that's going on. The system doesn't require Internet access. Everything works
fine in the secure local network.

If the system is free and open, what is your interest?
------------------------------------------------------

We have been engaged in the automation activities for both private and
enterprise sectors for many years. Our clients work with different systems,
including previous versions of EVA. The development of EVA 3 is a step towards
the unification of all configurations that we support and use ourselves.

We decided to distribute the new system completely free of charge, but we
provide a commercial support for the setups where the reliability is the
critical importance. We are also developing and integrating complex
configurations, create additional commercial EVA applications and interfaces
for a specific systems.

In addition, if:

* you want to become a system integrator and provide commercial support
* you want to distribute our system together with your device
* you want to make us an offer we can't refuse

you should `contact us <https://www.altertech.com/>`_ and we provide you a
siutable offer.

Is EVA complex and difficult to learn?
--------------------------------------

We try to make our system as simple and user-friendly as possible even for
those who have never encountered the process automation.

Is it reliable?
---------------

It is reliable enough for home and office setups, as well as for the small
industrial configurations, but if you use EVA on the enterprise, you should at
least understand the system well.

How about the security?
-----------------------

Traditionally, automation systems and protocols have been designed as not
completely secure. As for reliability, you may agree that it would be a pity if
the motor or door gets stuck because of incorrect access rights to a folder or
an expired SSL certificate. We recommend to have an optimal balance between
stability and :doc:`security</security>` and it's really different for the
every setup.

What programming languages can I use to write scripts and macros?
-----------------------------------------------------------------

As for :doc:`scripts</item_scripts>` - you can use any. Script or program runs
as a separate process in the system. It's only necessary that it reads the
input parameters correctly and writes the result in the appropriate format. If
you need a speed - PERL or DASH are preffered. If the speed is not so
important, you may use BASH or even PHP.

Logic Manager :doc:`macros</lm/macros>` are written in Python, but in most
cases, you'll need to call the internal macro functions only.

Besides, you can create your own applications working through API. The
distribution includes :doc:`API clients</api_clients>` for Python and PHP.

What if I have zero experience in programming?
----------------------------------------------

Programming for EVA is only about creating :doc:`item management
scripts</item_scripts>`. You can find plenty of examples in the documentation.

Additionally you need to program Logic Manager :doc:`macros</lm/macros>` for
the process automation. However, most macros have a very simple structure and
call the in-built set of functions.

For example, a macro that runs a pump for watering plants:


.. code-block:: python

    # call API action for pump1, controller will be identified automatically
    start('farm/pumps/pump1') 
    # reset the timer for watering
    reset('farm/pump1_run') 
    # message to the log file
    info ('watering cycle has been started') 
    # assign "watering" value to the production cycle variable
    set('farm/pump1_cycle', 'WATERING') 

As you can see, there is no rocket science.

What automation is all about? What are automation components?
-------------------------------------------------------------

The automation components mostly look like relay block, "smart" sockets,
"smart" switches - however, there is still some kind of relay inside. Usually,
there are 3 ports in the relay: input, two outputs, and two states: opened and
closed. In the first state, the signal passes through the first output, in the
second one - through the second. This is the main principle automation is based
on.

Sometimes equipment may include controlled resistors, so that the additional
parameters (e. g. light dimmer) should be set. In this case, you should
send the additional value to the controller, i.e. to set a definite percent of
capacity.

Our system works not with relay, but with the endpoint equipment that is
automated. The relay ports are programmed and switched with the help of
:doc:`scripts</item_scripts>`, which are written once during the installation.
Thereafter, the system works with the :ref:`units<unit>`.

Besides, any automation system has its "eyes" and "ears" for receiving data
from the environment and making its own decisions - humidity and temperature
:ref:`sensors<sensor>`, motion sensors etc.

In EVA, all decisions are made either by the user or :doc:`/lm/lm` subsystem.

Where is the interface? I want a web interface!
-----------------------------------------------

Each automated setup needs an interface. EVA has a very powerful
:doc:`/sfa/sfa` component, which combines the while setup itself and provides a
flexible :doc:`/sfa/sfa_framework` which allows you to create the modern
websocket-powered web interface with a few strings of javascript

.. code-block:: javascript

    eva_sfa_apikey = 'MY_VERY_SECRET_KEY';
    eva_sfa_init();
    eva_sfa_start();
    eva_sfa_register_update_state('sensor:env/temperature1',
        function(state) {
            $('#temp1').html(state.value);
        }

no rocket science as well.

