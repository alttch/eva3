.. EVA Documentation

EVA ICS documentation
=====================

`EVA ICS <https://www.eva-ics.com/>`_ is a platform for automated control and
monitoring systems development, for any needs, from home/office to industrial
setups. It is completely free for non-commercial use as well as for commercial,
on condition that enterprise integrates it on its own. The product is
distributed as an open source software and is available under
:doc:`EVA License</license>`.

Automated control systems are facing a new stage of evolution: IoT-devices
become interesting for those, who have never dealt with automation, cheap
programmable devices become reliable enough for industrial use, commercial
solutions move away from old protocols and involve computer networks instead.
We do not reform automation – we change the approach: taking the classical
technology as a basis, we simplify everything else to the maximum. Automation
is simple and available for everyone!

What is EVA
-----------

* :doc:`Universal controllers</uc/uc>` for management and monitoring of all
  your equipment, on the basis of which you can develop your own automation
  applications easily and quickly.

* :doc:`Notification system</notifiers>`, that instantly informs applications
  on current events.

* :doc:`Logic Manager</lm/lm>` programming logic controllers used for automatic
  data processing and decision-making.

* :doc:`SFA Framework</sfa/sfa_framework>` and :doc:`SFA
  Templates</sfa/sfa_templates>`, allowing quick development of the interfaces
  for a specific configuration.

EVA can be installed either partially or fully, it can be scaled up to many
servers or all components can be installed onto the only one. The system is
designed in such a way, that it can work on any hardware: from fat servers to
mini-computers with only one smart card in the “read-only” mode.

Architecture of EVA provides a high scalability: one system can support dozens
and even hundreds of thousands of devices through processing events via separate
subsystems and collecting all data to a unified database. 

The latest EVA ICS version is |Version|. :doc:`CHANGELOG</changelog>`

What you get with EVA
---------------------

* use pre-made :doc:`drivers</drivers>` or write simple
  :doc:`scripts</item_scripts>` for your automation hardware and keep them
  organized, queued and safely executed with :doc:`/uc/uc`
* easily collect data from the hardware using :ref:`MQTT<mqtt_>` or :doc:`SNMP
  traps</snmp_traps>` with the built-in SNMP trap handler server
* collect data from your microcontrollers with a simple :ref:`UDP
  API<uc_udp_api>`
* test and monitor the initial setup with controllers' EI web interfaces
* exchange all automation data between multiple servers with EVA controllers
  and your own apps via :ref:`MQTT<mqtt_>` server or :doc:`HTTP
  notifiers</notifiers>`
* use EVA :doc:`/lm/lm` to write powerful :doc:`macros</lm/macros>` which can
  be run automatically on events in accordance with the :doc:`decision
  rules</lm/decision_matrix>` you set up
* collect everything and control your whole setup with the :doc:`aggregator
  controllers</sfa/sfa>`
* :doc:`/api_clients` to quickly connect controllers' API to your apps
* develop a modern real-time websocket-powered SCADA web applications with
  :doc:`/sfa/sfa_framework`
* and much more

System documentation
--------------------

* :doc:`Installation</install>`

* :doc:`Security recommendations</security>`

* :doc:`Tutorial</tutorial/tutorial>`

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
    * :ref:`sensor` - monitored item
    * :ref:`device` - set of items
    * :doc:`/drivers` - drivers for hardware equipment
    * :doc:`/item_scripts` - action and update scripts
    * :doc:`ModBus equipment</modbus>`
    * :doc:`/virtual`

  * :doc:`/lm/lm` - a programmable logic controller

    * :doc:`/lm/lm_api` - API of the Logic Manager subsystem
    * :ref:`lvar` -  item used by system components to exchange logic data

    * :doc:`/lm/macros`
    * :doc:`/lm/ext`
    * :doc:`/lm/decision_matrix`

 * :doc:`/sfa/sfa` server

    * :doc:`/sfa/sfa_api` - API of the SCADA Final Aggregator
    * :doc:`/sfa/sfa_pvt` - Private data web server

* :doc:`/cli`

* Application development

    * :doc:`/api_clients`
    * :doc:`/sfa/sfa_templates`
    * :doc:`/sfa/sfa_framework`
    * :doc:`Physical interfaces for drivers</phi_development>`

* :doc:`/faq`
