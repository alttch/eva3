Installation
************

All you need to install EVA  is to download the latest update from
https://www.eva-ics.com/, unpack the archive to any folder and everything is
almost ready to use.

.. note::

    Each EVA ICS installation (**node**) can run multiple components. Despite
    they share node resources, they still act as independent processes and
    require :ref:`MQTT server<mqtt_>` for inter-connection.

.. contents::

System Requirements
===================

* Python version 3 (preferably 3.4+) or later, plus pip3 for automatic
  installation of the additional modules
* Linux or UNIX-compatible system
* For :doc:`/sfa/sfa_pvt` to work with images: libjpeg-dev and libjpeg8-dev
  (for PIL / `pillow <https://python-pillow.org/>`_ installation)
* `realpath <http://www.gnu.org/software/coreutils/realpath>`_ (available in
  all modern Linux distributions)
* EVA ICS can run on any Linux or UNIX-compatible system, but for the smooth
  install we recommend Ubuntu or Debian.
* Install system package *libow-dev* to let EVA ICS install owfs module.
* To sync :doc:`item</items>` status between the components in real time -
  :ref:`MQTT<mqtt_>`-server (e.g. `mosquitto <http://mosquitto.org/>`_)

.. warning::

    Installation scripts try to install all required Python modules
    automatically, but some of them can have problems installing with pip -
    install can fail or be slow. It's better to install these modules manually,
    before running EVA installation scripts. Currently the problems can be
    expected with:

        * **pandas** (python3-pandas)
        * **pysnmp** (python3-pysnmp4), version 4.4.x+ required
        * **cryptography** (python3-cryptography)

Initial setup
=============

.. note::

    If you are going to run any controllers under restricted user account,
    make sure it has a valid shell set.

Preparing the system
--------------------

Install required system packages and heavy Python modules from the OS
repository. here is an example how to install them on Debian-based Linux (i.e.
Ubuntu):

.. code-block:: bash

    apt install -y curl python3 python3-pip python3-pandas python3-pysnmp4 python3-cryptography jq

Installing local MQTT server
----------------------------

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

* mqtt host: localhost
* mqtt port: 1883 (default)
* mqtt user, password: leave empty
* mqtt space: leave empty
* mqtt ssl: leave empty (answer 'n' if using *easy-setup*)

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

Easy setup
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

Manual setup
------------

* Run *./install/install-without-setup* in EVA folder
* In *etc* folder copy *uc.ini-dist* into *uc.ini*; if you plan to use
  :doc:`/uc/uc`, change necessary configuration parameters.
* Copy *uc_apikeys.ini-dist* into *uc_apikeys.ini* and set the API keys
* Repeat the procedure for the configuration of :doc:`/lm/lm` and
  :doc:`/sfa/sfa`
* In etc folder copy *eva_servers-dist* into *eva_servers*, set *ENABLED=yes*
  for the chosen controllers, set *USER* params to run certain controllers
  under :doc:`restricted users</security>`.

.. code-block:: bash

    UC_ENABLED=yes
    LM_ENABLED=yes
    SFA_ENABLED=yes
    LM_USER=nobody
    SFA_USER=nobody

* Make sure all restricted users have an access to *log*, *var* and
  *runtime/db* folders as well to runtime files and folders plus to config
  files in *etc* (both <component>.ini and <component>_apikeys.ini).

* Setup log rotation by placing *etc/logrotate.d/eva-\** files to
  */etc/logrotate.d* system folder. Correct the paths to EVA files if
  necessary.
* Setup automatic launch at boot time by placing *EVADIR/sbin/eva-control
  start* command into system startup e.g. to */etc/rc.local* or place
  ./etc/systemd/eva-ics.service to /etc/systemd/system/ for systemd-based
  startup.

* Configure the :doc:`notification system</notifiers>` if required.

* Start EVA:

.. code-block:: bash

    ./sbin/eva-control start

The system is ready. Enable automatic launch in the same way as for
*easy-setup*.

.. note::

    To change or set up (without *easy-setup.sh*) the user controllers are
    running under, use *./set-run-under-user.sh* script to adjust runtime and
    database permissions.

Updating
========

Using EVA Shell
---------------

* Backup everything in system shell

* Launch EVA Shell (*/opt/eva/bin/eva-shell*)

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
    #curl -s https://get.eva-ics.com/3.2.0/stable/update.sh | bash /dev/stdin

* If updating from 3.0.2 or below, you may also want to enable controller
  watchdog (copy *etc/watchdog-dist* to *etc/watchdog* and edit the options if
  required)

.. note::

    The system downgrade is officially not supported and not recommended.

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

Log file customization
======================

Perform these on the installed Python modules to avoid any extra information in
logs:

* **dist-packages/ws4py/websocket.py** and **dist-packages/ws4py/manager.py** -
  replace all *logger.error* calls to *logger.info*

* **dist-packages/urllib3/connectionpool.py** - if you set up the controllers
  to bypass SSL verifications (don't do this on production!), remove or comment

         if not conn.is_verified:warnings.warn((....

Using NGINX as a frontend for SFA interface
===========================================

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
        ssl_protocols  SSLv3 TLSv1;
        ssl_ciphers  HIGH:!aNULL:!MD5;  
        ssl_prefer_server_ciphers   on; 

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
