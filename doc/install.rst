Installation
************

All you need to install EVA  is to download the latest update from
https://www.eva-ics.com/, unpack the archive to any folder and everything is
almost ready to use.

.. note::

    Each EVA ICS installation (**node**) can run multiple components. Despite
    they share node resources, they still act as independent processes and
    require inter-connection set up.

.. contents::

Officially supported platforms
==============================

Recommended for enterprise setups
---------------------------------

* `RedHat Enterprise Linux 8 <https://www.redhat.com/en/enterprise-linux-8>`_

* `Ubuntu Linux LTS 18.04/20.04 <https://ubuntu.com/>`_

Tested and fully compatible
---------------------------

* `Debian Linux 10 and newer <https://www.debian.org/>`_

* `Ubuntu Linux 18.10 and newer <https://ubuntu.com/>`_

* `Raspbian Linux <https://www.raspberrypi.org/>`_

* `Fedora Linux <https://getfedora.org/>`_

System Requirements
===================

.. important::

    Before installation, set the proper host name. It will be used to
    identify node controllers. Changing host name later will require manually
    removing/appending all static links between EVA ICS controllers.

* Python version 3 (3.6+)

* Python virtual environment modules (python3-virtualenv)

* Linux or UNIX-compatible system

* For :doc:`/sfa/sfa_pvt` to work with images: libjpeg-dev and libjpeg8-dev
  (for PIL / `pillow <https://python-pillow.org/>`_ installation)

* `realpath <http://www.gnu.org/software/coreutils/realpath>`_ (available in
  all modern Linux distributions)

* EVA ICS can run on any Linux or UNIX-compatible system, but for the smooth
  install we recommend Ubuntu or Debian.

* Install system package *libow-dev* to let EVA ICS install owfs module.

* To sync :doc:`item</items>` status between the controllers in different
  networks - :ref:`MQTT<mqtt_>`-server (e.g. `mosquitto
  <http://mosquitto.org/>`_) or to communicate with other equipment and 3rd
  party software.

.. warning::

    Installation scripts try to install all required Python modules
    automatically, but some of them can have problems installing with pip -
    install can fail or be slow. It's better to install these modules manually,
    before running EVA installation scripts. Currently the problems can be
    expected on ARM systems with:

        * **pandas** (python3-pandas)
        * **cryptography** (python3-cryptography)

    To let EVA ICS venv use system site modules, read instructions below.

Optional modules (can be disabled in :ref:`venv<install_venv>` configuration):

* **onewire** required for 1-Wire via :doc:`OWFS</owfs>`
* **pymodbus** required for :doc:`Modbus</modbus>` master/slave functions
* **pysnmp** required for SNMP client/server functions
* **pillow** required for :doc:`SFA PVT</sfa/sfa_pvt>` image processing

.. important::

   Make sure host temp directory has enough free space to build required Python
   modules. You may change temp directory location by setting TMPDIR
   environment variable.

Using installer
===============

Supported Linux distributions:

 * Debian/Ubuntu/Raspbian
 * Fedora

Automatic and unattended
------------------------

Install required system packages, setup EVA ICS components:

.. code-block:: bash

    sudo -s
    curl geteva.cc | sh /dev/stdin -a

Customized
----------

Customize API keys:

.. code-block:: bash

    sudo -s
    curl geteva.cc | env MASTERKEY=123 DEFAULTKEY=qwerty sh /dev/stdin -a

More options, interactive setup:

.. code-block:: bash

    sudo -s
    curl geteva.cc -o install.sh
    sh install.sh --help

E.g. install required system packages, setup :doc:`/uc/uc` only, use external
MQTT server and predefined API keys:

.. code-block:: bash

    sudo -s
    curl geteva.cc | \
        env MASTERKEY=mykey DEFAULTKEY=mydefaultkey sh /dev/stdin \
            --autostart --logrotate --bash-completion \
            -- --auto -p uc --mqtt eva:password@192.168.1.100 --mqtt-announce --mqtt-discovery

Manual installation
===================

.. note::

    If you are going to run any controllers under restricted user account,
    make sure it has a valid shell set.

Preparing the system
--------------------

Install required system packages and heavy Python modules from the OS
repository. here is an example how to install them on Debian-based Linux (i.e.
Ubuntu):

.. code-block:: bash

    apt install -y curl gcc python3 python3-dev python3-virtualenv python3-distutils jq libow-dev libjpeg-dev libjpeg8-dev

Configuring MQTT broker
-----------------------

:ref:`MQTT<mqtt_>` broker is used when EVA ICS controllers are located in
different networks and can not exchange data with P2P connections.

.. note::

    Starting from EVA ICS 3.2.3, MQTT broker for inter-connection of
    controllers which run on a single host/network is no longer required.

If EVA ICS node is already set up without MQTT configuration, you can add it
later with *easy-setup* or manually, using *eva ns* command.

Installing local MQTT server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you plan to use local MQTT server, here is an example how to install
`mosquitto`_ MQTT server on Debian-based Linux (i.e.
Ubuntu):

.. code-block:: bash

    apt install -y mosquitto
    # stop mosquitto
    /etc/init.d/mosquitto stop
    # let the server listen to localhost only
    echo "bind_address 127.0.0.1" >> /etc/mosquitto/mosquitto.conf
    # start mosquitto back
    /etc/init.d/mosquitto start
    # make sure mosquitto is running
    ps auxw|grep mosquitto

Options for EVA ICS:

* MQTT host: localhost
* MQTT port: 1883 (default)
* MQTT user, password: leave empty
* MQTT space: leave empty
* MQTT SSL: leave empty (answer 'n' if using *easy-setup*)

Cloud service provider as MQTT broker
-------------------------------------

* :doc:`/integrations/aws`

.. note::

    Cloud IoT services provide restricted broker functionality and don't
    guarantee event/message ordering. This means some *state* messages between
    controllers may be lost (discarded by controller core if newer message with
    the same topic is already received).

Downloading and extracting EVA ICS distribution
-----------------------------------------------

Go to `EVA ICS website <https://www.eva-ics.com/>`_, download most recent
distribution and unpack it e.g. to */opt/eva*:

.. code-block:: bash

    cd /opt
    curl https://get.eva-ics.com/3.x.x/stable/eva-3.x.x-xxxxxxxxxx.tgz -o eva.tgz
    tar xzvf eva.tgz
    mv eva-3.x.x eva
    cd eva

.. _install_venv:

Customizing Python virtual environment
--------------------------------------

Starting from 3.2.1, EVA ICS uses Python virtual environment (venv). This makes
software installation more stable, as it uses only tested versions of 3rd party
libraries.

EVA ICS installation script automatically creates Python virtual environment in
./python3 folder. It can be customized/recreated later manually, using command:

.. code-block:: bash

    ./install/build-venv

or

.. code-block:: bash

    eva feature setup venv
    
If you want to rebuild venv from scratch, delete *python3* folder completely.

On some systems (e.g. ARM-based computers) venv installation can be tricky: you
can expect slow installation time or problems with some heavy modules (e.g.
*pandas*, *cryptography*).

To solve this:

* If you already run the installation and it has failed, delete *./python3*
  folder.

* Go to *./etc* folder, copy *venv-dist* to *venv* and customize virtual
  environment options.

    * **USE_SYSTEM_PIP=1** allows to use system-installed pip3 (*apt-get install
      python3-pip*) in case installation script has a problems downloading /
      installing it.

    * **PYTHON=python3** here you may specify custom Python executable.

    * **SYSTEM_SITE_PACKAGES=1** virtual environment will use system site
      packages if their versions match with requested.

    * **SKIP** here you can specify the packages (in quotes, space separated),
      which should be skipped (e.g.  *pandas cryptography* and install it with
      *apt-get install python3-pandas python3-cryptography* instead). To let
      venv use system package, *SYSTEM_SITE_PACKAGES=1* should also be present.

    * **EXTRA** extra modules to install, e.g. required by :ref:`PHIs<phi>`,
      used by :doc:`logic macros</lm/macros>` or :doc:`macro
      extensions</lm/ext>` etc.

    * **PIP_EXTRA_OPTIONS** specify extra options for *pip3*, e.g. *-v* for
      verbose installation.

.. note::

    Customize venv only if you have serious problems installing EVA ICS with
    default options, as the system may became unstable when versions of 3rd
    party libraries are different from tested.

Options, specified in *./etc/venv* are also used by EVA ICS update scripts,
which check/rebuild venv on every system update.

Installing
----------

.. warning::

    If you want to run some components under restricted users, create **var**
    and **log** folders in EVA installation dir and make sure the restricted
    users have an access to these folders before running *easy-setup*. If
    you've customized ini files in *etc*, make sure the restricted user has an
    access to both <component>.ini and <component>_apikeys.ini.

    If you want to make some initial customization, e.g. name the controllers
    different from the host name, make changes in *etc/uc.ini*, *etc/lm.ini*
    and *etc/sfa.ini* configs first.

* For the interactive setup, run *./easy-setup* in EVA folder and follow the
  instructions.
* For the automatic setup, run *./easy-setup -h* in EVA folder and choose
  the installation type.

Setup log rotation by placing *etc/logrotate.d/eva-\** files to
*/etc/logrotate.d* system folder. Correct the paths to EVA files if necessary.

.. code-block:: bash

    cp ./etc/logrotate.d/eva-* /etc/logrotate.d/

Setup automatic launch at boot time by placing *EVADIR/sbin/eva-control start*
command into system startup e.g. either to */etc/rc.local* on System V, or for
systems with *systemd* (all modern Linux distributions):

.. code-block:: bash

    cp ./etc/systemd/eva-ics.service /etc/systemd/system/
    systemctl enable eva-ics

Unicode
-------

EVA ICS supports unicode out-of-the-box. If your system has problems, rebuild
locales and then restart EVA ICS controllers:

.. code-block:: bash

    sudo dpkg-reconfigure locales
    sudo eva server restart


Updating
========

.. warning::

    Before updating from the previous version, read `update
    manifest <https://github.com/alttch/eva3/blob/3.3.2/UPDATE.rst>`_.

Using EVA Shell
---------------

* Backup everything in system shell

* Launch EVA Shell (*/opt/eva/bin/eva-shell* or *eva -I*)

* Backup configuration (type *backup save* command in EVA Shell)

* Type *update* command in EVA Shell

.. note::

    EVA ICS repository URL has been changed to https://get.eva-ics.com. If
    you've got "Update completed" message but update process hasn't even been
    started, try executing *update* command specifying EVA ICS repository
    directly:
    
    *update -u https://get.eva-ics.com*

Using system shell
------------------

* Backup everything
* Run the following command:

.. code-block:: bash

    curl -s <UPDATE_SCRIPT_URL> | bash /dev/stdin
    #e.g.
    #curl -s https://get.eva-ics.com/3.3.2/stable/update.sh | bash /dev/stdin

* If updating from 3.0.2 or below, you may also want to enable controller
  watchdog (copy *etc/watchdog-dist* to *etc/watchdog* and edit the options if
  required)

.. note::

    The system downgrade is officially not supported and not recommended.

With a pre-downloaded tarball
-----------------------------

Put *update.sh* and the new version tarball to EVA ICS root directory
(/opt/eva). Run the update:

.. code-block:: bash

    ./update.sh

The script will use tarball located in EVA ICS directory. If the required
version tarball file doesn't exists, it will be downloaded.

To prepare Python venv and explore new version files (e.g. may be required for
the offline updating), run

.. code-block:: bash

    env CHECK_ONLY=1 bash update-xxxxxxx.sh

The script will exit after preparing the virtual environment. The new version
files will be kept in *_update* directory.

Intermediate versions
---------------------

It is usually absolutely safe to update old EVA ICS installations to newer
version without applying all intermediate updates.

However, it is highly recommended to read update manifests for all skipped
versions and combine before / after update instructions.

Moving to another folder
========================

EVA ICS doesn't depend on any system paths, this allows to easy rename or move
its folder or clone the installation. Just do the following:

* stop EVA ICS (*./sbin/eva-control stop*)
* rename, move or copy EVA ICS folder
* if you've copied the folder, edit configuration files to make sure components
  use different ports and/or interfaces
* start EVA ICS back (*./sbin/eva-control start*)
* correct logrotate and on-boot startup paths

Setting up additional features
==============================

Some optional features require installing additional modules and system
libraries and putting the proper settings in EVA ICS configuration files.

This process can be automated with "eva feature" command, which provides small
code snippets to quickly setup or remove a chosen feature.

For example, to setup *net-snmp* library (speeds up some supported SNMP
:doc:`PHI modules </drivers>`), type:

.. code:: bash

    eva feature setup netsnmp

Full list of feature snippets can be obtained with command:

.. code:: bash

    eva feature list-available

Watchdog
========

Watchdog process is started automatically for each EVA controller and tests it
with the specified interval. Controller should respond to API call **test**
within the specified API timeout or it is forcibly restarted.

Watchdog configuration is located in file *etc/watchdog* and has the following
params:

* **WATCHDOG_INTERVAL** checking frequency (default: 30 sec)
* **WATCHDOG_MAX_TIMEOUT** maximum API timeout (default: 5 sec)
* **WATCHDOG_DUMP** if the controller is not responding, try to create crash
  dump before restarting (default: no).

How to assign IDs to items
==========================

All system :doc:`items</items>` including :doc:`macros</lm/macros>` have their
own ids. Item id should be unique within one server in **simple**
:ref:`layout<item_layout>`. When using **enterprise** layout, it is possible
for items to have the same id in different groups, however full item id
(*group/id*) should be always unique within one controller.

.. note::

    Before adding items, consider what kind of :ref:`layout<item_layout>` you
    want to use: simple or enterprise

    Starting from 3.2.0, the default item layout is **enterprise**. The simple
    layout is deprecated.

Item groups can coincide and often it is convenient to make them similar: for
example, if you set *groups=security/#* in API key config file, you will allow
the key to access all the items in the security group and its subgroups
regardless of whether it is macro, sensor or logic variable. To set access to
a group of particular items, use oids, e.g. *groups=sensor:security/#*.

This does not apply to :doc:`decision rules</lm/decision_matrix>` and
:doc:`macros</lm/macros>`: a unique id is generated for each rule
automatically, macro id should be always unique.

.. note::

    The triple underline (**___**) is used by system and should not be used in
    item IDs or groups.

.. _install_cloud:

Cloud setup
===========

Configuring LM and SFA as primary
---------------------------------

:doc:`/lm/lm` and :doc:`/sfa/sfa` nodes can monitor and control items on
different nodes. :doc:`/uc/uc` instances can be connected to both, while LM PLC
instances can be connected to SFA only.

The components can be connected to each other either P2P, via HTTP or via
:ref:`MQTT <mqtt_>`. Usually in production setups, MQTT is the most secure and
recommended way, unless for components running on the localhost.

On the primary node (the node you want to connect other nodes to), MQTT
notifier can be configured either with "easy-setup" or manually. Let's
manually configure MQTT notifier for SFA, with automatic discovery feature:

.. code:: bash

    eva -I # go interactive
    ns sfa
    create eva_1 mqtt:MQTT_HOST # set login/password/SSL if required
    set eva_1 discovery_enabled 1
    test eva_1 # test should pass
    enable eva_1
    server restart

After restart, SFA is ready to accept cloud member controllers.

Configuring UC and LM PLC as secondaries
----------------------------------------

To automatically connect controllers from the secondary node, they must have
the same "default" API key. So, secondary node installation should look like:

.. code-block:: bash

    sudo -s
    curl geteva.cc | env DEFAULTKEY=qwerty sh /dev/stdin -a

Setting the same master key is insecure and not recommended unless all nodes
are in absolutely trusted environment.

The local components' default key can be quickly changed later with a command:

.. code:: bash

    eva feature setup default_key key=NEW_SECRET_DEFAULT_KEY

Automatic default cloud configuration for the local UC and LM PLC instances:

.. code:: bash

    eva feature setup default_cloud mqtt=user:password@192.168.1.12

Manual MQTT notifier configuration (e.g. for UC):

.. code:: bash

    eva -I # go interactive
    ns uc
    create eva_1 mqtt:MQTT_HOST # set login/password/SSL if required
    set eva_1 announce_interval 30 # announce itself every 30 seconds
    set eva_1 api_enabled 1 # accept API calls via MQTT
    subscribe server eva_1 # subscribe to server events
    subscribe state eva_1 -g '#' # subscribe to item states from all groups
    test eva_1 # test should pass
    enable eva_1
    server restart

After restart, the controller will be seen in connected LM PLC and SFA as
"dynamic". That means the controller record disappears after each restart. To
set controller connection permanent, set its property "static" to "true" (or
"1"):

.. code:: bash

    eva sfa controller set uc/ucnode1 static 1 -y

The secondary controller is also set automatically as static, when the primary
one is configured as a Cloud manager and the secondary's property "masterkey"
is set.

Cloud manager
-------------

A primary :doc:`/sfa/sfa` instance is called cloud manager. There can be more
than one Cloud manager in the cloud, having different secondary controllers
with different permissions connected.

The cloud manager (enabled by default in *etc/sfa.ini* section "cloud",
option "cloud_manager = yes"), provides two features:

* The cloud manager interface is enabled on SFA node at
  \http://SFA_IP:SFA_PORT/cloudmanager/ (the default port is 8828).

* SFA can set "masterkey" property for secondary controllers collected. This
  allows SFA to send them managing and advanced control commands.

Cloud manager allows to manage the whole cloud from the one node. Cloud manager
is required for :doc:`/iac`.

Master key for components of a specified node connected can be automatically
set with a command:

.. code::

    eva feature setup node_masterkey node=plant1,key=NODE_MASTER_KEY

Cloud updates
-------------

A command, run on Cloud manager node:

.. code-block:: bash

    eva sfa cloud update

allows to run updates on all nodes connected.

* Despite EVA ICS never applies update unless the system is checked and ready,
  the cloud update should be used with extremely caution in production setups.

* All nodes should have either the Internet connection or a valid :ref:`local
  mirror <install_mirror>` set up.

* The nodes are always updated to the latest EVA ICS version available, so if
  your setup requires particular versions for all of them, consider using the
  local mirror.

* As industrial computers may be slow and controllers may be busy, sometimes
  "cloud update" could produce false warnings and errors, e.g. when it expects
  a remote controller to already have a new version installed, while it was not
  even shot down for update yet. It is recommended to play with
  "--shutdown-delay" and "--check-timeout" command options to find the best
  combination for your setup.

Log file customization
======================

Perform these on the installed Python modules to avoid any extra information in
logs:

* **dist-packages/ws4py/websocket.py** and **dist-packages/ws4py/manager.py** -
  replace all *logger.error* calls to *logger.info*

* **dist-packages/urllib3/connectionpool.py** - if you set up the controllers
  to bypass SSL verifications (don't do this on production!), remove or comment

         if not conn.is_verified:warnings.warn((....

.. _install_frontend:

Using NGINX as a frontend for SFA interface
===========================================

.. note::

    To properly log IP addresses of the requests, make sure the front-end sets
    *X-Real-IP* header and set *[webapi]/x_real_ip=yes* option in
    :ref:`sfa_ini`.

External authentication
-----------------------

Suppose `NGINX <https://www.nginx.com/>`_ operates on 8443 port with SSL, and
:doc:`/sfa/sfa` - without SSL. Let's make the task even more complicated: let
NGINX receive the request not directly, but via port forwarding from the router
listening on an external domain (i.e. port 35200).

Additionally, we want to authorize:

* by IP address or
* basic auth by username/password or
* by cookie-token (required for EVA Android Client since it passes basic auth
  only when the server is requested for the first time)

The server should allow access upon the authorization of any type.

Our final config for all of this should look like:

.. code-block:: nginx

    map $cookie_letmein $eva_hascookie {
      "STRONGSECRETRANDOMTOKEN" "yes";
      default           "no";      
    }

    geo $eva_ip_based {            
      192.168.1.0/24 "yes"; # our internal network
      default        "no";
    }

    map $eva_hascookie$eva_ip_based $eva_authentication {
      "yesyes" "off"; # cookie and IP matched - OK
      "yesno"  "off"; # cookie matched, IP did not - OK
      "noyes"  "off"; # cookie did not match, IP did - OK
      default  "?"; # everything else - demand the password 
    }

    upstream eva-sfa {
            server 127.0.0.1:8828;
    }

    server {
        listen 192.168.1.1:8443;
        server_name  eva;
        ssl                  on;
        ssl_certificate /opt/eva/etc/eva.crt;
        ssl_certificate_key /opt/eva/etc/eva.key;
        ssl_session_timeout  1m;

        # proxy for HTTP
        location / {
            auth_basic $eva_authentication; 
            auth_basic_user_file /opt/eva/etc/htpasswd;
            add_header Set-Cookie "letmein=STRONGSECRETRANDOMTOKEN;path=/";
            proxy_buffers 16 16k;
            proxy_buffer_size 16k;
            proxy_busy_buffers_size 240k;   
            proxy_pass http://eva-sfa;
            # a few variables for backend, though in fact EVA requires X-Real-IP only
            proxy_set_header X-Host $host;  
            proxy_set_header Host $host;    
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header X-Frontend "nginx";
            proxy_redirect http://internal.eva.domain/ui/ https://external.eva.domain:35200/ui/;
        }

        # proxy for WebSocket
        location /ws {
            auth_basic $eva_authentication; 
            auth_basic_user_file /opt/eva3/etc/htpasswd;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_buffers 16 16k;
            proxy_buffer_size 16k;
            proxy_busy_buffers_size 240k;   
            proxy_pass http://eva-sfa;      
            proxy_set_header X-Host $host;  
            proxy_set_header Host $host;    
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header X-Frontend "nginx";
        }
    }

Using HTTP basic auth for EVA ICS authentication
------------------------------------------------

The following example demonstrates how to use basic authentication and
automatically log in user into SFA UI.

Firstly, set *user_hook* option in *./etc/sfa.ini*, this will allow EVA ICS to
sync htpasswd file with SFA users (make sure *htpasswd* program is installed as
well).

.. code-block:: ini

    [server]
    .......
    user_hook = /opt/eva/xbin/htpasswd.sh /opt/eva/etc/htpasswd

Then, front-end config (e.g. for NGINX) should look like:

.. code-block:: nginx

    upstream eva-sfa {
            server 127.0.0.1:8828;
        }

    server {
        listen 80 default_server;

        location / {
            auth_basic $eva_authentication;
            auth_basic_user_file /opt/eva/etc/htpasswd;
            rewrite ^/pvt/(.+)$ /pvt?f=$1 last;
            proxy_buffers 16 16k;
            proxy_buffer_size 16k;
            proxy_busy_buffers_size 240k;
            proxy_pass http://eva-sfa;
            proxy_set_header X-Host $host;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-Proto http;
            proxy_set_header X-Port $server_port;
            proxy_set_header X-Frontend "nginx";
        }

        location /ws {
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_buffering off;
            proxy_pass http://eva-sfa;
            proxy_set_header X-Host $host;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-Proto http;
            proxy_set_header X-Port $server_port;
            proxy_set_header X-Frontend "nginx";
        }
    }

With such setup, :ref:`js_framework`-based interface doesn't perform any
authentication, *$eva.start()* function is called as soon as UI is loaded.
API method *login* called by framework function will automatically log in user
using basic authentication credentials provided to front-end server.

.. _install_mirror:

Serving local mirror
====================

If secondary nodes have unstable, slow or no Internet connection, the local
mirror can be configured. The mirror can be hosted by nodes, where
:doc:`/sfa/sfa` is set up. The SFA node, which hosts the mirror, must have the
Internet connection.

The mirror hosts both EVA ICS distribution and all required Python modules +
their dependencies.

After creation / update, the mirror hosts EVA ICS version / build, which the
primary node has got. It is possible to host the mirror for a single version
only.

For the secondary nodes with the Internet connection, using mirrors is not
required.

Installing
----------

The mirror is automatically created with a command:

.. code:: bash

    eva mirror update

The same command is also used to update mirror files.

.. note::

    If the mirror wasn't used before, the local SFA controller must be
    restarted to serve the mirror directory:

    .. code:: bash

        eva sfa server restart

The mirror should be updated every time after the host node is update. There is
also "-M" flag for "eva update" command to perform the mirror update
automatically.

Configuring mirror
------------------

The local mirror duplicates settings from "etc/venv". Modules from "SKIP"
section are not mirrored, modules from "EXTRA" section are included.

This means if any node uses extra Python modules, it is better to include them
in "EXTRA" section of "etc/venv" of the node the mirror is configured on.

.. note::

    After adding extra modules, update mirror with "eva mirror update" command.

If secondary nodes have different Python version than the mirror node, put
Python versions (comma-separated) into "etc/eva_shell.ini" before creating /
updating the mirror:

.. code::

    [update]
    mirror_extra_python_versions = 3.7, 3.9

This will ask "mirror update" to download binary modules for the specified
Python versions as well.

If the cluster contains nodes with different architectures, it is recommended
to forcibly mirror sources of the all modules, including "source" option in
Python version list:

.. code::

    [update]
    mirror_extra_python_versions = 3.7, 3.9, source

.. note::

    GNU C Lib (Ubuntu/Debian/RedHat etc.) and musl libc (Alpine and similar)
    are considered as the different architectures.

Configuring secondary nodes
---------------------------

After updating, EVA shell tries to determine the local SFA IP address / port
and automatically gives configuration instructions. In complicated setups,
IP/port may differ and need to be corrected manually.

.. note::

    The mirror can be used only by secondary nodes with the same CPU
    architecture.

If the mirror is set up properly, the following url should display a web page
with EVA ICS version and build:

    \http://<SFA_IP>:<PORT>/mirror/

Automatic setup
~~~~~~~~~~~~~~~

On secondary node, type:

.. code:: shell

    eva mirror set http://<SFA_IP>:<PORT>/mirror/

Note that the above command overrides *PIP_EXTRA_OPTIONS* in *etc/venv*.

To switch back to the default EVA ICS and PyPi mirrors, type:

.. code:: shell

    eva mirror set default

Manual setup
~~~~~~~~~~~~

Setting up PyPi mirror location
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On secondary nodes, open "etc/venv" file and add *PIP_EXTRA_OPTIONS* field, as
given by mirror update command. If the field already exists, merge existing
options with the new:

    PIP_EXTRA_OPTIONS="-i \http://<SFA_IP>:<PORT>/mirror/pypi/local --trusted-host <SFA_IP>"

Setting up EVA ICS repository location
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Secondary nodes must to be updated with "-u
\http://<SFA_IP>:<PORT>/mirror/eva" extra option for "eva update"
command.

It is also possible to configure the default repository location, by editing
the file "etc/eva_shell.ini" (copy it from *eva-shell.ini-dist*, if doesn't
exists), section "update", field "url":

.. code:: ini

    [update]
    url = http://<SFA_IP>:<PORT>/mirror/eva

Removing
--------

Remove "mirror" in EVA ICS directory:

.. code:: bash

    rm -rf /opt/eva/mirror

Optionally, restart the local SFA instance after.
