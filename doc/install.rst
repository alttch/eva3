Installation
============

Everything you need to install EVA  is to download the latest update from
https://www.eva-ics.com/, unpack the archive to any folder and everything is
almost ready to use.

.. contents::

System Requirements
-------------------

* Python version 3 (preferably 3.4+) or later, plus pip3 for the automatic
  installation of the additional modules
* Linux or UNIX-compatible system * For :doc:`/sfa/sfa_pvt` to work with
  images: libjpeg-dev and libjpeg8-dev (for PIL / `pillow
  <https://python-pillow.org/>`_ installation)
* `realpath <http://www.gnu.org/software/coreutils/realpath>`_ (available in
  all modern Linux distributions)
* EVA ICS can run on any Linux or UNIX-compatible system, but for the smooth
  install we recommend Ubuntu or Debian.
* To sync :doc:`item</items>` status between the components in real time -
  :ref:`MQTT<mqtt_>`-server (i.e. `mosquitto <http://mosquitto.org/>`_)

.. warning::

    Installation scripts try to install all required Python modules
    automatically, but some of them may have problems installing with pip -
    install may fail or be slow. It's better to install these modules manually,
    before running EVA installation scripts. Currently the problems may be
    expected with:

        * **pandas** (python3-pandas)
        * **pysnmp** (python3-pysnmp4)

Initial configuration
---------------------

.. note::

    If you are going to run any controllers under restricted user account,
    make sure it has a valid shell set.


Easy setup
~~~~~~~~~~

* For the interactive setup, run *./easy-setup.sh* in EVA folder and follow the
  instructions.
* For the automatic setup, run *./easy-setup.sh -h* in EVA folder and choose
  the installation type.
* Setup log rotation by placing *etc/logrotate.d/eva-\** files to
  */etc/logrotate.d* system folder. Correct the paths to EVA files if
  necessary.
* Setup automatic launch at boot time by placing *EVADIR/sbin/eva-control
  start* command into system startup i.e. to */etc/rc.local*.

.. note::

    If you want to make some initial customization, i.e. name the controllers
    different from the host name, make a changes in *etc/uc.ini*, *etc/lm.ini*
    and *etc/sfa.ini* configs first.

Manual setup
~~~~~~~~~~~~

* Run *./install.sh* in EVA folder
* In *etc* folder copy *uc.ini-dist* into *uc.ini*; if you plan to use
  :doc:`/uc/uc`, change the necessary configuration parameters.
* Copy *uc_apikeys.ini-dist* into *uc_apikeys.ini* and set the API keys
* Repeat the procedure for the configurations of :doc:`/lm/lm` and
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

* Setup log rotation by placing *etc/logrotate.d/eva-\** files to
  */etc/logrotate.d* system folder. Correct the paths to EVA files if
  necessary.
* Setup automatic launch at boot time by placing *EVADIR/sbin/eva-control
  start* command into system startup i.e. to */etc/rc.local*.

* Configure the :doc:`notification system</notifiers>` if required.

* Start EVA:

.. code-block:: bash

    ./sbin/eva-control start

The system is ready.

.. note::

    To change or set up (without *easy-setup.sh*) the user controllers are
    running under, use *./set-run-under-user.sh* script to adjust runtime and
    database permissions.

Upgrading
---------

To version 3.1.0 and above
~~~~~~~~~~~~~~~~~~~~~~~~~~

* Backup everything
* Run the following command:

.. code-block:: bash

    curl -s <UPGRADE_SCRIPT_URL> | bash /dev/stdin
    #i.e.
    #curl -s https://www.eva-ics.com/download/3.1.0/stable/upgrade.sh | bash /dev/stdin

* If upgrading from 3.0.2 or below, you may also want to enable controller
  watchdog (copy *etc/watchdog-dist* to *etc/watchdog* and edit the options if
  required)

To versions below 3.1.0
~~~~~~~~~~~~~~~~~~~~~~~

* Stop EVA: *./sbin/eva-control stop*
* Backup eva installation folder
* Unpack new version to the folder where EVA is installed
* Execute *sh install.sh* to install missed modules
* Restore custom scripts and **ui** folder if required
* Start EVA: *./sbin/eva-control start*

.. note::

    The system downgrade is officially not supported and not recommended.

How to assign IDs to items
--------------------------

All system :doc:`items</items>` including :doc:`macros</lm/macros>` have their
own ids. Item id should be unique within one server.

Ideally, item id should also be unique in the whole system, but if
cross-controller access control to the certain items is not critical or is
implemented through the groups, different items on different servers (for
example, logic variable on one LM PLC and sensor on another) can have the same
id.

Item groups can coincide and often it is convenient to make them similar: for
example, if you set *groups=security/#* in API key config file, you will allow
the key to access all the items in the security group and its subgroups
regardless of whether it is macro, sensor or logic variable.

The best practice is always to use unique id for the item i.e.
*office1.room1.temperature1* and use groups only for better item filtering.

This does not apply to the decision rules: an unique id is generated for each
rule automatically.

Log file customization
----------------------

Perform these on the installed Python modules to avoid any extra information in
logs:

* **dist-packages/ws4py/websocket.py** and **dist-packages/ws4py/manager.py** -
  replace all *logger.error* calls to *logger.info*

* **dist-packages/urllib3/connectionpool.py** - if you set up the controllers
  to bypass SSL verifications (don't do this on production!), remove or comment

         if not conn.is_verified:warnings.warn((....

Using NGINX as a frontend for SFA interface
-------------------------------------------

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
