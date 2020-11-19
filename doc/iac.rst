IaC and deployment
******************

EVA ICS supports infrastructure-as-code paradigm, providing a way to deploy
items and their params from deployment files in YAML format.

Live deployment examples can be found in EVA ICS demos:

* https://github.com/alttch/eva-demo-smarthome
* https://github.com/alttch/eva-demo-farm

Deployment is possible only on :doc:`SFA</sfa/sfa>` servers.

.. note::

    To allow deployment, SFA must have child controllers connected in
    management mode (connected controllers master keys should be set). Also,
    cloud manager feature should be enabled in SFA configuration file.

.. contents::

Deployment configuration file
=============================

Deployment configurations are stored in YAML files, which have the following
format:

Controllers
-----------

Section *controller* contains:

* :doc:`Driver</drivers>` setup for :doc:`/uc/uc`
* Commands, executed after configuration deployment

Common variables setup
~~~~~~~~~~~~~~~~~~~~~~

Here's an example to set two cvar values:

.. code:: yaml

    controller:
        uc/controller1:
            cvar:
                var1: value1
                var2: value2

Driver setup
~~~~~~~~~~~~

Here is an example, which:

* Loads two PHI *vrtrelay* modules into :doc:`/uc/uc` *uc/controller1* as *vr1*
  and *vr2*. The second module has configuration option *state_full=true*.
* Creates *vr1.opener* driver using *vr1* PHI module and *multistep* LPI.

.. code:: yaml

    controller:
        uc/controller1:
            phi:
                vr1:
                    module: vrtrelay
                    # src: path/to/module
                vr2:
                    module: vrtrelay
                    config:
                        state_full: true
            driver:
                vr1.opener:
                    module: multistep
                    config:
                        bose: true

"src" field tells deployment function to get PHI module from file or URL and
upload it to the target controller.

Uploading files
~~~~~~~~~~~~~~~

Local files can be uploaded into remote controller runtime directory:

.. code:: yaml

    controller:
        uc/controller1:
            upload-runtime:
                - localfile:remotefile
                - localfile2:path/to/remotefile2

File list: local/remote files, separated with ":". If remote directory doesn't
exist, it will be created automatically.

It's possible to use masks for local files, e.g. in the example below, contents
of "bundle" directory will be uploaded to remote node "runtime/upload",
directory structure will be duplicated as-is.

.. code:: yaml

    controller:
        uc/controller1:
            upload-runtime:
                - bundle/*:upload/

.. note::

    To upload directory contents recursively, set file mask to \*\*

Before/After deploy
~~~~~~~~~~~~~~~~~~~

Controller API calls may be automatically executed after deployment is
complete:

.. code:: yaml

    controller:
        lm/lm1:
            before-deploy:
                - { api: reset, i: timers/timer1 }
            after-deploy:
                - { api: clear, i: timers/timer1 }
                - { api: reload_controller, i: uc/uc1 }
                - { api: reload_controller, i: uc/uc2 }
                - { api: custom_fn, _pass: true, param1: 123, param2: "x" }

API calls are always executed in the specified order, one-by-one, *api:* field
contains API function to execute, others specify function parameters. The
special parameter *_pass* in the last call allows deployment to ignore failed
API call (warning will be printed).

.. note::

    It is usually recommended to call *reload_controller* for :doc:`/lm/lm` to
    let it instantly load newly deployed items from connected UCs.

Additional deploy functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

sleep
^^^^^

Delays execution of next before/after deploy commands. E.g. let's reload remote
UC and wait 5 seconds until its core is restarted:

.. code:: yaml

    controller:
      uc/uc1:
        after-deploy:
          - api: shutdown_core
          - function: sleep
            args: [ 5 ]

system
^^^^^^

Executes (local) system command:

.. code:: yaml

    controller:
      uc/uc1:
        after-deploy:
          - function: system
            args: [ 'ls' ]

Items
-----

:doc:`/items` can be deployed with *unit*, *sensor* and *lvar* sections. All
sections are similar, the format is:

.. code:: yaml

    unit:
        group1/u1:
            controller: uc/uc1
            action_enabled: true
            update_interval: 0
            status: 0 # initial status, optional
            driver:
                id: vr1.default
                config:
                    port: 1

All child fields specify item properties, except:

* Field *controller* specifies controller, where item should be deployed
* For units and sensors, *driver* field may be used to assign driver to the
  item.

If *action_exec* or *update_exec* values are started with *^* symbol, it tells
deployment tool to upload local file on the controller.

The second example shows how to deploy a sensor and logical variable:

.. code:: yaml

    sensor:
        group1/s1:
            controller: uc/uc1
            driver:
                id: somedriver.default
                config:
                    port: 1
                value: 77 # initial value, optional, initial status for sensor
                          # is not required (automatically set to 1 - enabled)

    lvar:
        group1/timer1:
            controller: lm/lm1
            expires: 30
            status: 0 # initial status, optional
            value: 77 # initial value, optional

Macros
------

:doc:`/lm/macros` are deployed in *lmacro* section:

.. code:: yaml

    lmacro:
        group1/macro1:
            controller: lm/lm1
            action_exec: ^macro1.py

All child fields specify item properties, except:

* Field *controller* specifies :doc:`/lm/lm`, where macro should be deployed

If field *action_exec* value is started with *^* symbol, it tells deployment
tool to upload local file on the controller.

.. note::

    To make deployment process more easy, it is recommended to start it in
    directory, where macro files are located.

Logical rules
-------------

:doc:`/lm/decision_matrix` can be configured with *dmatrix_rule* section.

Rule example:

.. code:: yaml

    dmatrix_rule:
      5ef9b8fd-d527-44ce-ae89-9629afd40d76:
          controller: lm/farm-scada
          description: light normal
          enabled: true
          oid: sensor:#/ldr/value
          condition: x = 1
          break_after_exec: true
          macro: stop_lamp

All child fields specify item properties, except:

* Field *controller* specifies :doc:`/lm/lm`, where rule should be configured

Rule UUID should be pre-generated with any UUID generator, e.g. with *uuidgen*
Linux console command.

How to deploy configuration
===========================

Currently there is no API functions for deploy EVA ICS configuration. The item
configuration can be deployed either via :doc:`CLI</cli>` or during
installation.

Deployment via CLI
------------------

Deploying
~~~~~~~~~

Deployment configuration can be applied using  *eva sfa cloud deploy* command.
When deployed with :doc:`CLI</cli>`, deployment file may contain variables.

Example:

.. code:: yaml

    unit:
        light/room1:
            controller: uc/{{ srv }}

Here is *srv* variable defined. To set its value, e.g. to "uc1", use *-c
srv=uc1* command line argument. If multiple variable values are set, they
should be comma separated, e.g.: *-c srv1=uc1,srv2=uc2* etc.

There's also command line argument *-u* which tells CLI to try undeploying
target configuration before doing deployment of it. Undeployment process
ignores missing items and deletes only existing.

Undeploying
~~~~~~~~~~~

Deployment configuration can be removed with *eva sfa cloud undeploy* command.
Custom variable values can be set in the same way as during deployment.

Deployment during installation
------------------------------

Configuration also can be deployed with *easy-setup* during
:doc:`SFA</sfa/sfa>` :doc:`installation</install>`. Use *--deploy FILE* command
line argument to specify path to the deployment file.

Complex deployments
-------------------

Bare-metal
~~~~~~~~~~

Sometimes deployment is more complex than just creating items. In this case
deployment scripts are used to prepare environment, call *eva sfa cloud deploy*
command and finish deployment.

Containers
~~~~~~~~~~

There is no problems when the regular bare-metal or virtual machine
installation is performed, but if EVA ICS is being installed into Docker
machine or Kubernetes cluster, there is a special environment variable
*after_install*, which tells `EVA ICS Docker
image <https://hub.docker.com/r/altertech/eva-ics>`_ to execute deployment
script after installation process is finished. Here's an example part of
docker-compose file:

.. code:: yaml

    eva-scada:
        environment:
            - after_install=/deploy/deploy.sh

Devices
-------

Starting from EVA ICS 3.3.2, :ref:`device<device>` template format is equal to
IaC files.

For cvar deployment, a proper "controller" property should be present in the
device template. In "unit" and "sensor" sections, "controller" property is not
required and ignored if present.
