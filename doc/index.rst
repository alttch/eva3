EVA ICS documentation
*********************

`EVA ICS <https://www.eva-ics.com/>`_ is a platform for automated control and
monitoring systems development, for any needs, from home/office to industrial
setups. It is completely free for non-commercial use as well as for commercial,
on condition that enterprise integrates it on its own. The product is
distributed as a free software and is available under Apache License 2.0.

Automated control systems are facing a new stage of evolution: IoT-devices
become interesting for those, who have never dealt with automation, cheap
programmable devices become reliable enough for industrial use, commercial
solutions move away from old protocols and involve computer networks instead.
We do not reform automation – we change the approach: taking the classical
technology as a basis, we simplify everything else to the maximum. Automation
is simple and available for everyone!

What is EVA
===========

* :doc:`Universal controllers</uc/uc>` for management and monitoring of all
  your equipment, on the basis of which you can develop your own automation
  applications easily and quickly.

* :doc:`Notification system</notifiers>`, that instantly informs applications
  on current events.

* :doc:`Logic Manager</lm/lm>` programming logic controllers used for automatic
  data processing and decision-making.

* :ref:`js_framework` and :doc:`SFA Templates</sfa/sfa_templates>`, allowing
  quick development of the interfaces for a specific configuration.

EVA can be installed either partially or fully, it can be scaled up to many
servers or all components can be installed onto the only one. The system is
designed in such a way, that it can work on any hardware: from fat servers to
mini-computers with only one smart card in the “read-only” mode.

Architecture of EVA provides a high scalability: one system can support dozens
and even hundreds of thousands of devices through processing events via separate
subsystems and collecting all data to a unified database. 

The latest EVA ICS version is |Version|. :doc:`CHANGELOG</changelog>`

What you get with EVA
=====================

* powerful :doc:`command-line interface (CLI)<cli>`
* use pre-made :doc:`drivers</drivers>` or write simple
  :doc:`scripts</item_scripts>` for your automation hardware and keep them
  organized, queued and safely executed with :doc:`/uc/uc`
* easily collect data from the hardware using :ref:`MQTT<mqtt_>` or
  :ref:`snmp_traps` with the built-in SNMP trap handler server
* collect data from your microcontrollers with a simple :doc:`UDP
  API</uc/uc_udp_api>`
* test and monitor the initial setup with controllers' EI web interfaces
* exchange all automation data between multiple servers with EVA controllers
  and your own apps via :ref:`MQTT<mqtt_>` server or :doc:`JSON
  notifiers</notifiers>`
* use EVA :doc:`/lm/lm` to write powerful :doc:`macros</lm/macros>` which can
  be run automatically on events in accordance with the :doc:`decision
  rules</lm/decision_matrix>` you set up
* collect everything and control your whole setup with the :doc:`aggregator
  controllers</sfa/sfa>`
* :doc:`/api_clients` to quickly connect controllers' API to your apps
* develop a modern real-time websocket-powered SCADA web applications with
  :ref:`js_framework`
* set up IoT cloud with nodes connected via :ref:`MQTT<mqtt_cloud>`
* and much more

.. toctree::
    :caption:  System Documentation
    :maxdepth: 1

    install
    What's new <changelog>
    security
    notifiers
    cli
    tutorial/tutorial
    faq
    highload

.. toctree::
    :caption:  Components
    :maxdepth: 1

    uc/uc
    lm/lm
    sfa/sfa
    items

.. toctree::
    :caption:  Equipment management
    :maxdepth: 1

    drivers
    item_scripts
    modbus
    owfs
    snmp
    virtual

.. toctree::
    :caption:  Logic control
    :maxdepth: 1

    lm/macros
    lm/decision_matrix
    lm/jobs
    lm/cycles

.. toctree::
    :caption:  Interface development
    :maxdepth: 1

    sfa/sfa_templates
    sfa/sfa_pvt
    api_tokens
    evahi
    EVA JS Framework <https://github.com/alttch/eva-js-framework>

.. toctree::
    :caption:  Integrations
    :maxdepth: 1

    integrations/aws
    integrations/cctv
    integrations/gcp
    integrations/grafana
    integrations/tts

.. toctree::
    :caption:  Extension development
    :maxdepth: 1

    sysapi
    uc/uc_api
    uc/uc_udp_api
    lm/lm_api
    sfa/sfa_api
    uc/uc_api_restful
    lm/lm_api_restful
    sfa/sfa_api_restful
    api_clients
    Physical interfaces for drivers <phi_development>
    Logic macro extensions <lm/ext>
