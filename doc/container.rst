EVA ICS container
*****************

The Docker container image of EVA ICS is available at
https://hub.docker.com/r/altertech/eva-ics

The image is compatible with both `Docker <https://www.docker.com>`_ standalone
and `Kubernetes <https://kubernetes.io>`_.

Basic usage example: https://github.com/alttch/eva-demo-basic

Permanent volumes
=================

The following volumes can be permanent (mounted from the host):

* ui
* pvt
* backup
* runtime
* etc
* log
* var

The permanent volumes must be mounted to the container as */mnt/VOL*

Configuration variables
=======================

The following variables can be set in the container environment to configure
the system (for the first launch only):

* MASTERKEY - system master key
* DEFAULTKEY - system default key
* DEPLOY - path or URI to a deployment YAML file

System name is automatically set according to the container host name.

Prepare / setup scripts
=======================

When the container is started for the first time or updated, the following
scripts are executed automatically if exist and mounted:

* /setup/prepare.sh - if exists, executed before the system setup (EVA ICS
  registry is already started)

* /setup/rc.local - if exists, is copied to the container and executed at every
  container launch (after EVA ICS registry startup, before controllers startup)

* /setup/setup.sh - if exists, executed after the system setup (EVA ICS
  registry and controllers are already started)

If "DEPLOY" variable is used, the automatic deployment is performed after all
setup scripts are finished.

Updating
========

Roll out a new container image. The included update script automatically
updates EVA ICS configuration during the first start. As the image contains all
EVA ICS and required libraries and modules, Internet connection is not
required, unless any custom modules are required.
