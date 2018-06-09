.. EVA Documentation

EVA ICS documentation
=====================

`EVA ICS <https://www.eva-ics.com/>`_ is a platform for automated control and
monitoring systems development, for any needs, from home/office to the
industrial setups. It is completely free for non-commercial use as well as for
commercial, on condition that enterprise integrates it on its own. The product
is distributed as open source software and available under
:doc:`EVA License</license>`.

Automated control systems are facing a new stage of evolution: IoT-devices
become interesting for those, who have never dealt with automatization, cheap
programmable devices become reliable enough for the industrial use, commercial
solutions move away from old protocols and involve computer networks instead.
We do not reform automation – we change the approach: taking the classical
technology as a basis, we simplify everything else to the maximum. Automation
is simple and available for everyone!

What is EVA
-----------

* :doc:`Universal controllers</uc/uc>` for the management and monitoring of all
  your equipment, on the basis of which you can develop you’s own automation
  applications easily and quickly.

* :doc:`Notification system</notifiers>`, that instantly informs applications
  on current events.

* :doc:`Logic Manager</lm/lm>` programming logic controllers used for the
  automatic data processing and decision-making.

* :doc:`SFA Framework</sfa/sfa>`, allowing quick development of the interfaces
  for a specific configuration.

EVA can be installed either partially or fully, it can bescaled up to many
servers or all components can be installed onto the only one. The system is
designed in such a way, that it can work on any hardware: from the fat servers
to mini-computers with only one smart card in the “read-only” mode.

Architecture of EVA provides a high scalability: one system can support dozens
and even hundreds of thousands of devices through processing events via separate
subsystems and collecting all data to the unified database. 

The latest EVA ICS version is |Version|. :doc:`CHANGELOG</changelog>`

System documentation
--------------------

* :doc:`Installation</install>`

* :doc:`Security recommendations</security>`

* :doc:`Tutorial</tutorial/intro>`

* System components

  * :doc:`/uc/uc`
  * :doc:`/lm/lm`
  * :doc:`/sfa/sfa`

* :doc:`items`

* API and system objects

  * :doc:`/sys_api` - common API for all subsystems
  * :doc:`/notifiers` - a link between subsystems and third-party applications
  * :doc:`/uc/uc` - a  management and monitoring controller

    * :doc:`/uc/uc_api` - API of the Universal Controller subsystem
    * :ref:`unit` - controlled item
    * :ref:`sensor` - monitoring item
    * :doc:`/item_scripts` - action and update scripts
    * :doc:`/virtual`

  * :doc:`/lm/lm` - a programmable logic controller

    * :doc:`/lm/lm_api` - API of the Logic Manager subsystem
    * :ref:`lvar` -  item used by system components to exchange information
    * :doc:`/lm/macros`
    * :doc:`/lm/decision_matrix`

 * :doc:`/sfa/sfa` server

    * :doc:`/sfa/sfa_api` - API of the Scada Final Aggregator
    * :doc:`/sfa/sfa_pvt` - Private data web server

* :doc:`/cli`

* Application development

    * :doc:`/api_clients`
    * :doc:`/sfa/sfa_framework`

* :doc:`/faq`
