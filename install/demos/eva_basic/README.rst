EVA ICS demo: Basic
*******************

Layout
======

This demo deploys single EVA ICS node with UC, LM PLC and SFA installed.

Node configuration is empty.

Network and containers
======================

* **eva_mqtt** local MQTT server (mosquitto), *10.27.5.200*
* **eva_1** EVA ICS node, *10.27.5.10:*

Deployment
==========

Requirements: `Docker <https://www.docker.com/>`_, `docker-compose
<https://docs.docker.com/compose/>`_.

Download and extract demo file:

.. code-block:: bash

  curl https://get.eva-ics.com/demos/eva_basic.tgz -o eva_basic.tgz
  tar xzvf eva_basic.tgz
  cd eva_basic

Execute *docker-compose up* to deploy containers

Management
==========

http://10.27.5.10:8828 - SFA API/primary operator interface (empty, framework
files only).

From command line: *docker exec -it eva_1 eva-shell*

Default masterkey is: *demo123*

Components:

* http://10.27.5.10:8812 - UC API/EI
* http://10.27.5.10:8817 - LM PLC API/EI

