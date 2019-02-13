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

