Notification system
*******************

The Notification System is embedded in all EVA subsystems. All the events of
these subsystems are sent to the notification servers via objects called
"notifiers" which contain the configuration of the notification endpoints.

.. contents::

Event structure
===============

Each event includes the following data:

* **Event subject** (not to be confused with :ref:`MQTT<mqtt_>` subject)
* **Notification space** May be used to divide the controlled structure into
  sectors, e.g. city1/office1, plant1 etc. By dividing spaces you can separate
  one EVA installation from another using the same notification server, e.g. to
  create your own multi-control and multi-monitoring systems.
* **Event data** (usually JSON dict with) data on what's actually happened

Event subjects
--------------

There are several event subjects in EVA. Each notification endpoint can be
subscribed either to one of them or to several ones.

state - item state change event
-------------------------------

The event notifications with the "state" subject are sent by :doc:`/uc/uc` and
:doc:`/lm/lm` whenever the :doc:`items<items>` change their status.

Notification sends data similar to those, one can get using :doc:`/uc/uc_api`
or :doc:`/lm/lm_api` state.  There is one difference for a
:ref:`sensors:<sensor>`: sensor with error status (status = -1) does not send
its value data until the value is null. This was done specifically for the
logic components to work correctly with the old value until the sensor
status data is updated correctly and the sensor is back online or until the
data is expired.

action - unit and macro action events
-------------------------------------

Every time the :ref:`unit<unit>` :ref:`action<ucapi_action>` or :doc:`macro
action</lm/macros>` changes its :ref:`status<uc_queues>`, the notification
server receives "action" event notification.

Notification sends data similar to ones that can be obtained using UC API
:ref:`result<ucapi_result>` command.

log - logged event
------------------

When the system or you add record to the logs, the notification system sends
'log' event notification. The log notification data have the following format:

.. code-block:: text

    {
     "h": "<SYSTEM_NAME>",
     "l": <LEVEL>,
     "p": "<PRODUCT_CODE>",
     "msg": "<message body>",
     "mod": "<MODULE>",
     "th": "<MODULE_THREAD>",
     "t": <TIME(UNIX_TIMESTAMP)>,
     "dt": <TIME RFC3339>
    }

* **SYSTEM_NAME** the name specified in the configuration file of controller
  (or hostname by default)
* **LEVEL** 10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR or 50 for CRITICAL
* **PRODUCT_CODE** "uc" for :doc:`/uc/uc`, "lm" for :doc:`/lm/lm`, "sfa" for
  :doc:`/sfa/sfa`
* **MODULE** a specific system module, e.g. 'unit'
* **MODULE_THREAD** the module thread, e.g. "_t_action_processor_lamp1"

Important: the system does not send the log records related to the notification
system itself. They are not visible via EI interfaces and are written
only into the local log files. This was done for the notification system not to
send the records in cycles.

server - server events
----------------------

Server events are used to notify controllers and clients about system events.
Event format is simple:

.. code-block:: text

    {
      "s": "server",
      "d": "<event>"
    }

Event data for MQTT notifiers is packed as dict:

.. code-block:: text

    {
      "s": "server",
      "d": {
        ... system data ...
        e: "<event>"
        }
    }

Configuring the notification endpoints
======================================

Configuration is done using the :doc:`console commands</cli>` uc-notifier for
:doc:`/uc/uc`, lm-notifier for :doc:`/lm/lm` and sfa-notifier for
:doc:`/sfa/sfa` or **eva ns <uc|lm|sfa>**. Therefore, even if two controllers
are set up in the same folder on the same server, they have different
notification endpoints configurations.

Basic Configuration
-------------------

Let's play with notification system e.g. of :doc:`/uc/uc`. This command will
give us the list of notifiers, including their types, IDs, status and endpoint
target.


    # eva ns uc list

    ========        ========        ========     ========
    Type            ID              Status       Target
    ========        ========        ========     ========
    mqtt            eva_1           Enabled      eva:test@localhost:1883/lab
    ========        ========        ========     ========
   
Let's test the endpoint (for mqtt the system will try to publish [space]/test)

    # eva ns uc test eva_1
    OK

To create the new notifier configuration, run:

    eva ns uc create [-s SPACE] [-t SEC] [-y] ID PROPS

where

* **ID** the unique ID of the notifier
* **PROPS** endpoint properties, e.g. mqtt:[username:password]@host:[port]
* **-s SPACE** notification space
* **-t SEC** timeout (optional)

Option *"-y"* enables the notification configuration right after creation (by
default all notifiers are created as disabled)

The notifier configuration params may be viewed with *props* and changed with
*set* notifier CLI commands. To apply the changes you must restart the
controller.

Except for endpoint configuration, notifiers have some additional params:

* **collect_logs** this should be set to "true" for :doc:`/sfa/sfa`
  :ref:`MQTT<mqtt_>` notifiers if you want to collect the logs of other
  controllers and have the records available locally in SFA.
* **interval** when set, notifier will send subscribed item states with the
  specified interval
* **notify_key** notification key for custom http endpoints
* **skip_test** if "true", the endpoint won't be tested at the controller start
  (the controller keeps the notifier active but puts error into the log)

Subscribing the notifier to events
----------------------------------

By default, the new notifier is not subscribed to any events. You can
review all the subscriptions using "get_config" command.

To subscribe notifier to the new subject, run:

    eva ns uc subscribe <subject> <notifier_id> [args]

    (where subject is "state", "log" or "action")

When subscribing notifier to logs, you may use optional *-l LEVEL* param (10 -
DEBUG, 20 - INFO, default, 30 - WARNING, 40 - ERROR, 50 - CRITICAL).

When subscribing notifier to state changes, you may also always specify item
types (comma separated) or use '#' for all types with *-p TYPE* param, groups
with *-g GROUPS*. Optionally you may specify the particular items to subscribe
notifier to with *-I ITEMS*.

.. note::

    For each "state" subscription you must specify either type and groups or
    item IDs.

Example:

    eva ns uc subscribe state test1 -p '#' -g 'hall/#'

subscribes the notifier *test1* to the events of the status change of all the
items in the *hall* group subgroups.

Subscription to "action" requires the params similar to "state". Additionally,
*-a '#'* should be specified to subscribe to all the action statuses or *-a
state1,state2,state3...* to subscribe to the certain statuses of the
:ref:`queued actions:<uc_queues>`.

For example, the following command will subscribe the notifier to the events of
all failed actions:

.. code-block:: bash

    eva ns uc subscribe action test2 -p '#' -g '#' -a dead,refused,canceled,ignored,failed,terminated

Once created, the subscription can't be changed, but new subscription to the
same subject replaces the configuration of the previous one.

To unsubscribe the notifier from the subject, run:

    eva ns uc unsubscribe [subject] <notifier_id>

If the subject is not specified, the notifier will be unsubscribed from all
notification subjects.

The controller should be restarted to apply the new subscriptions
configuration.

.. _mqtt_:

MQTT (mqtt)
===========

MQTT is a major endpoint type used to link several EVA subsystems. For
instance, it enables :doc:`/lm/lm` and :doc:`/sfa/sfa` controllers to
receive the latest item status from :doc:`/uc/uc` servers when set on a nodes
in different networks. We test and use EVA with `mosquitto
<http://mosquitto.org/>`_ server, but you can use any server supporting `MQTT
<http://mqtt.org/>`_ protocol. As far as MQTT is the major type of the EVA
notification system, let us examine it in detailed.

MQTT and state notifications
----------------------------

:doc:`Items<items>` in MQTT form a subject hive so-called "EVA hive". Hive may
have a space e.g. "plant1/" to separate several EVA systems which use the same
MQTT server.

Item's state is stored in a hive with the subject
*SPACE/item_type/group/item_id* and contains the item state data and some
configuration params in JSON array.

By default, MQTT notifier creates a subscription per item to avoid processing
of unnecessary topics. If the cloud contains lots of items which need to be
synchronized with the local controller, sometimes it is useful to set
**subscribe_all** notifier option to *true*. If set, notifier is subscribed to
all possible item state and control topics using wildcards. This may cause more
overhead on the controller side, but reduces MQTT server load.

MQTT and action notifications
-----------------------------

:ref:`Unit<unit>` action notifications are sent to the topic

    SPACE/unit/group/UNIT_ID/action

:doc:`Logic macros</lm/macros>` action notifications are sent to the topic

    SPACE/lmacro/group/UNIT_ID/action

These messages include the serialized action information in JSON format. As
soon as action state is changed, the new notification is sent.

MQTT and log notifications
--------------------------

Log messages are sent to the MQTT server as JSON with the following MQTT
subject:

    SPACE/log
    
It means that the common log subject is created for one EVA space.

Any EVA server (usually it's a job for :doc:`/sfa/sfa`) can be a log collector,
collecting the reports from MQTT server (space/log), pass them further via the
local notification system and have them available via API. In order to enable
this function, set param *collect_logs* to true in the notifier configuration:

    sfa-notifier set eva_1 collect_logs true

Setting up MQTT SSL
-------------------

If MQTT server requires SSL connection, the following notifier properties
should be set:

* **ca_certs** CA certificates file (e.g. for Debian/Ubuntu:
  */etc/ssl/certs/ca-certificates.crt*), required. SSL client connection is
  enabled as soon as this property is set.

* **certfile** SSL certificate file, if required for authentication

* **keyfile** SSL key file for SSL cert

Setting up MQTT QoS
-------------------

You may specify different :ref:`MQTT<mqtt_>` QoS for events with different
subjects.

To set the same QoS for all events, use command:

    eva ns uc <notifier_id> set qos <Q>

    (where Q = 0, 1 or 2)

To set QoS for the specified subject, use command:

    eva ns uc <notifier_id> set qos.<subject> <Q>

e.g.

    eva ns uc eva_1 set qos.log 0

Quick facts about MQTT QoS:

* **0**  the minimum system/network load but does not guarantee message
  delivery
* **1** guarantees message delivery
* **2**  the maximum system/network load which provides 100% guarantee of
  message delivery and guarantees the particular message has been delivered
  only once and has no duplicates.


Use MQTT for updating item states
---------------------------------

MQTT is the only EVA notifier type performing two functions at once: both
sending and receiving messages.

:doc:`items` can use MQTT to change their state (for synchronization) if the
external controller can send active notifications under this protocol.

The items change their state to the state received from MQTT, if someone sends
its state update to EVA hive with *status* or *value* subtopics. Setting item
state with primary topic (using JSON dict) is not recommended.

To let the item receive MQTT state updates, set its **mqtt_update**
configuration param to the local MQTT notifier ID, as well as additionally
optionally specify MQTT QoS using a semicolon (i.e. *eva_1:2*). QoS=1 is used by
default.

State updates should be sent either to MQTT topics "path/to/unit/status" and
"path/to/unit/value" or as JSON message to "path/to/item". In example, to set
sensor "env/temp" value to 25:

    * MQTT topic: *sensor/env/temp*
    * MQTT payload:

        .. code:: json

            { "value": 25 }

As item value is always stored / exchanged as a string, it can be set via MQTT
in any convertible format.

.. note::

    There is also a configuration parameter *mqtt-update-default* which can be
    set in *config/<controller>/main* :doc:`registry</registry>` keys (default
    e.g. to *eva_1:2*) and applied to all newly created items.

One item can be subscribed to a single MQTT notifier to get the state updates,
but different items on the same controller can be subscribed to different MQTT
notifiers.


MQTT and unit actions
---------------------

MQTT can be also used as API to send actions to the :ref:`units<unit>`. In
order to send an action to the unit via MQTT, send a message with the
following subject: *[space]/<group>/<unit_id>/control* and:

* either in a form of text messages "status [value] [priority]". If you want to
  skip value, but keep priority, set it to null, i.e. "status 0 null 50".
  "value" and "priority" parameters are optional. If value should be omitted,
  set it to "none".

* or in JSON format (fields "value" and "priority" are optional):

    .. code:: json

        { "status": 1, "value": "", "priority": 100 }

In case you need 100% reliability, it is not recommended to control units via
MQTT, because MQTT can only guarantee that the action has been received by MQTT
server, but not by the target :doc:`/uc/uc`. Additionally, you cannot obtain
action uuid and further monitor it.

To let unit responding to MQTT control messages, set its configuration param
**mqtt_control** to the local MQTT ID. You may specify QoS as well via
semicolon, similarly as for **mqtt_update**.

.. _mqtt_bulk:

MQTT and bulk events
--------------------

To send events in :ref:`bulk<bulk_notify>`:

* set *buf_ttl* notifier option to the desired buffering time

* on secondary controllers (senders) set *bulk_topic* notifier option to any
  value (e.g.. *state/all*)

* on primary controllers (receivers) set *bulk_subscribe* notifier option to
  the same value (the option can have multiple values, set as comma separated)

.. _mqtt_cloud:

IoT Cloud setup
---------------

Special properties of MQTT notifiers allow to set up a cloud and connect EVA
ICS nodes via MQTT instead of HTTP:

* **announce_interval** if greater than zero, controller will announce itself
  with a chosen interval (in seconds) via MQTT to other cloud members.
* **api_enabled** allows controller to execute API calls from other cloud
  members via MQTT.
* **discovery enabled** controller will connect other nodes in cloud as soon as
  discover them.

To use auto discovery feature, API key named *default* must be present and
equal on all nodes.

API calls via MQTT are encrypted with strong AES256 algorithm, this allows to
use any 3rd party MQTT servers without any risk.

Optionally, controller can be a member of different clouds via different MQTT
notifiers.

.. _lurp:

UDP notifiers (LURP)
====================

Starting from EVA ICS 3.4, there is a lightweight UDP notifier, which pushes
events with simple UDP packets. In EVA ICS this method is called LURP
(Lightweight UDP Replication Protocol).

LURP is very fast and lightweight, however can cause data loss in unstable
networks. Actually, Using LURP is equal of using :ref:`MQTT notifiers<mqtt_>`
with QoS 0, but without the central data exchange point and with more
lightweight UDP packets.

To enable LURP, create "udp" notifier on secondary controllers (senders) and
enable LURP ports on primary controllers (receivers) in :ref:`LM PLC
config<lm_config>` or :ref:`SFA config<sfa_config>`.

If :ref:`bulk notifications<bulk_notify>` are used, make sure LURP buffer
option is enough to fit the largest expected data packet, otherwise data
packets with size exceeding buffer are received broken and ignored.

Turning on LURP does not mean that controllers stop sending events via other
methods. To stop sending events via MQTT, unsubscribe MQTT notifiers from
selected topics. To stop sending events via web sockets, set controller prop
option (on the receiver) *ws_state_events* to *false*.

To quickly turn on LURP for inter-connection on a local machine, the following
command can be used:

.. code:: shell

    eva feature setup lurp_local

The command automatically creates required notifier and reconfigures receivers,
it also turns off web socket state events for local controllers.

DB Notifiers
============

RDBMS (SQLite, MySQL, PosgreSQL)
--------------------------------

EVA ICS has a special notifier type: **db**, which is used to store items'
state history. State history can be obtained later via API calls or
:ref:`js_framework` for analysis and e.g. to build graphical charts.

To create db notifier, specify notifier props as **db:<db_uri>**,
e.g. *db:runtime/db/history1.db*, where *runtime/db/history1.db* - database
file in **runtime** folder.

DB notifier properties:

* **keep** keep records for the specified number of seconds. If keep time is
  not specified, EVA keeps records for last 86400 seconds (24 hours).

* **simple_cleaning** by default, records are analyzed before deletion to make
  sure each item will have at least one state metric in database after cleanup.
  This may cause additional overhead for the heavy loaded setups. Setting the
  property to *true* tells EVA to delete old records with a single query,
  ignoring that some of the items could have no records left after.

After creating db notifier, don't forget to subscribe it to **state** events.
Events **action** and **log** are ignored.

If **easy-setup** is used for EVA :doc:`installation</install>`, notifier
called **db_1** for :doc:`SFA</sfa/sfa>` is created automatically, default
History database format is `sqlite3 <https://www.sqlite.org/index.html>`_.

.. note::

    To create default (sqlite) db notifier, you may specify either database
    absolute path or relative to EVA ICS directory. *sqlite:///* prefix is
    optional and will be added automatically if missing.

EVA ICS db notifiers work via `SQL Alchemy <https://www.sqlalchemy.org/>`_, so
MySQL and PosgreSQL data storage is also supported.

E.g. to use MySQL, specify db uri as:

.. code::

    mysql+pymysql://username:password@host/database

(pymysql Python module is required)

or

.. code::

    mysql+mysqldb://username:password@host/database

(mysqlclient Python module is required)

If you get "failed to create state_history table" error with MySQL/MariaDB, try
setting:

.. code-block:: sql

    set global innodb_file_format=Barracuda;
    set global innodb_large_prefix=1;
    set global innodb_default_row_format=dynamic;

or put these options to database server configuration file.

TimescaleDB
-----------

`Timescale <https://www.timescale.com>`_ is a plugin for PosgreSQL, which can
be used to speed up time series data frames.

"timescaledb" notifier is absolutely equal to RDBMS PosgreSQL notifier, except
history functions use built-in methods of Timescale, instead of processing data
by themselves.

.. _influxdb_:

InfluxDB
--------

Version 1
~~~~~~~~~

Item state metrics can be stored to `InfluxDB <https://www.influxdata.com/>`_
time series database.

Consider InfluxDB is installed on local host, without password authentication.
Firstly, create database for EVA ICS:

.. code-block:: sql

    influx
    > create database eva

Then create InfluxDB notifier, e.g. for :doc:`/sfa/sfa`:

.. code-block:: bash

    eva ns sfa create influx_local 'influxdb:http://127.0.0.1:8086#eva'
    eva ns sfa test influx_local
    eva ns sfa subscribe state influx_local -g '#'
    eva ns sfa enable influx_local
    eva sfa server restart

That's it. After restart, :doc:`/sfa/sfa` immediately starts sending metrics to
the specified InfluxDB.

Then you can downsample metrics of the required item, e.g. let's downsample
*sensor:env/temp1* to 30 minutes:

.. code-block:: sql

    CREATE RETENTION POLICY "daily" ON "eva" DURATION 1D REPLICATION 1
    CREATE CONTINUOUS QUERY "downsampled_env_temp1_30m" ON "eva" BEGIN
      SELECT mode(status) as "status",mean(value) as value
      INTO "daily"."sensor:env/temp1"
      FROM "sensor:env/temp1"
      GROUP BY time(30m)
    END

After, you can tell :ref:`state_history <sfapi_state_history>` SFA API function
to select metrics from *daily* retention policy, specifying additional
parameter *o={ "rp": "daily" }*.

.. warning::

    It is highly recommended to set notifier "interval" property, to properly
    handle states for the rarely updated items.

.. _prometheus_:

Version 2
~~~~~~~~~

InfluxDB version 2 setup is easy as well:

.. code:: bash

    # setup the defaults
    influx setup
    # create a bucket
    influx bucket create -n eva
    # create a user
    influx user create -n eva -p verysecretpassword
    # create authentication policy, copy the auth token
    influx auth create -u eva --read-buckets eva --write-buckets eva

    # creave v1 dbrp mappings (optional)
    influx v1 dbrp create --bucket-id <id_of_eva_bucket> --db eva --default --rp default

EVA ICS notifiers for InfluxDB v2.x are similar to v1.x, except:

* EVA ICS can work with InfluxDB v2 both via v1 dbrp mappings and with new v2
  API.

* Token authentication is preferred (set "token" property of the notifier) and
  can be used for both v1 and v2 InfluxDB API.

* When EVA ICS notifier is created as:

  .. code:: bash

    eva ns sfa create influx_local 'influxdb:http://127.0.0.1:8086#orgname/bucket'

  v2 API is automatically used.

* API can be switched on-the-flow by setting "api_version" property of the
  notifier (EVA ICS controller needs to be restarted).

* For v2 API, "org" property of the notifier MUST be filled.

* As v2 API returns data in the own flux-csv format, using v1 API is slightly
  more resource-optimized.

* Some v2 functions (e.g. "mean") changed its behavior, so historical data
  results for InfluxDB v1 and v2 may be slightly different.

Prometheus
----------

EVA ICS can export metrics for `Prometheus <https://prometheus.io/>`_ time
series database.

To enable metrics export, create notifier for Prometheus (in the example below
we'll secure it with user/password authentication):

.. code-block:: bash

    eva ns sfa create pr1 prometheus:
    eva ns sfa test pr1
    eva ns sfa set pr1 username prometheus
    eva ns sfa set pr1 password 123
    eva ns sfa subscribe state pr1 -g '#'
    eva ns sfa enable pr1
    eva sfa server restart

After controller restart, metrics are available at URI
*/ns/<notifier_id>/metrics*. As Prometheus collect metrics by itself, EVA ICS
Prometheus notifier just exports subscribed item states to the specified
metrics URI every time when it's requested.

For the example above, Prometheus job config will look like:

.. code-block:: yaml

    scrape_configs:
    # .....
      - job_name: 'eva'
        scrape_interval: 5s
        metrics_path: /ns/pr1/metrics
        basic_auth:
          username: 'prometheus'
          password: '123'
        static_configs:
          - targets: ['localhost:8828']

Notes about using EVA ICS and Prometheus:

* As Prometheus doesn't support "/" and ".*" for metrics, EVA item properties
  are exported as e.g. *sensor:env:hum1_int:value*

* Only float and null item values are exported

* To enable metric help, set item description

3rd party Clouds
================

.. _gcpcoreiot_:

Google Cloud Platform IoT Core
------------------------------

Controllers can communicate with GCP IoT Core using *gcpiot* notifiers:

* Send telemetry of EVA ICS items to GCP devices
* Receive commands from GCP

Configuration
~~~~~~~~~~~~~

To enable this functionality, firstly you must `generate RSA256 key pair
<https://cloud.google.com/iot/docs/how-tos/credentials/keys>`_.

As GCP IoT Core doesn't support groups, create YAML key-value map file which
looks like:

.. code:: yaml

    env.pressure: sensor:env/air_pressure
    env.temperature: sensor:env/temperature
    cctv1: unit:equipment/cctv
    lamp1: unit:lights/lamp1

Then configure GCP IoT:

* Create IoT registry in your project. Specify default telemetry topic from
  which you can obtain data via Pub/Sub. Make sure *MQTT* option is checked.

* Create IoT gateway:

    * gateway name should match EVA ICS notifier id (e.g. *gcpiot*)
    * set *Device authentication method* to *Association only*
    * paste public key you've generated, make sure *RSA256* is selected.

* Create corresponding IoT devices. Enter *Device ID* only, leave other fields
  blank.

* Go back to IoT gateway and bind all created devices.

Configure EVA ICS, e.g. let's create notifier for :doc:`/uc/uc`:

.. code:: shell

    eva -I
    ns uc
    create gcpiot gcpiot:PROJECT_ID/REGION/REGISTRY
    # set CA certificate file
    set gcpiot ca_certs /etc/ssl/certs/ca-certificates.crt
    # set generated private RSA256 key file for auth
    set gcpiot keyfile /path/to/private.pem
    # set mapping file
    set gcpiot mapfile /path/to/mapfile.yml
    # test it
    test gcpiot
    # subscribe notifier to items
    subscribe state gcpiot -g '#'
    # set API key if you plan to execute commands
    # you may use use $key_id to specify key id instead of API key itself
    set gcpiot apikey $default
    # enable notifier
    enable gcpiot
    # restart controller
    server restart

Commands
~~~~~~~~

You may send commands as to EVA ICS controller (Gateway->Send command) as to
the individual devices.

* All commands must be sent in `JSON RPC 2.0 <https://www.jsonrpc.org>`_
  format.

* You may send any API command, e.g. for the above example: for :doc:`/sysapi`
  and for :doc:`/uc/uc_api`.

* API key in params is not required if set in notifier configuration, but
  may be overriden if specified.

* If you send command to the particular IoT device (EVA ICS item), parameter
  *"i"* (item oid) is automatically added to the request.

E.g., let's toggle *unit:equipment/cctv*:

.. code:: json

    {"jsonrpc": "2.0", "method": "action_toggle" }


HTTP Notifiers
==============

JSON
----

HTTP notifications (aka web hooks) are used by applications, which, for some
reasons, cannot work with MQTT in real time, e.g. servers containing
third-party or your own web applications.

JSON notifier send POST request to specified URI with data:

* **k** notification key the remote app may use to authorize the sender (if
  set)
* **space** notification space (if set)
* **subject** event subject
* **data** event data array

Your application must respond with JSON if the event has been processed
successfully (if empty response body is received, request is considered as
successful):

.. code-block:: json

    { "ok" : true }

or if your app failed to process it:

.. code-block:: json

    { "ok" : false }

or with HTTP status 202 (Accepted).

The event *data* field is always an array and may contain either one event or
several ones.

When EVA controllers test remote http-json endpoint, they send notifications
with subject="test" and the remote app should always respond with { "ok": True
} and HTTP status 200 (OK).

Example of custom notification processing server with Python and `Flask
<http://flask.pocoo.org/>`_:

.. code-block:: python

    from flask import Flask, app, request, jsonify

    app = Flask(__name__)

    @app.route('/json', methods=['POST'])
    def j():
        data = request.json
        # process notification request
        return jsonify({'ok': True})

NDJSON
------

If notification endpoint accepts only list (ndjson) data, set *method=list* in
JSON notifier properties. In this case, all above fields are included in each
notification data row.

This allows to send, process and collect EVA ICS logs, state telemetry and
other data as HTTP `NDJSON <http://ndjson.org/>`_ (Newline Delimited JSON)
stream, which is compatible with various data collectors, processors and
aggregators.

JSON RPC
--------

If notifier **method** property is set to *jsonrpc*, JSON RPC 2.0 call is
performed. For JSON RPC, errors must be specified in "error" field of the
response. For successful calls, the "result" field in response may contain any
data.

Example:

.. code-block:: python

    from flask import Flask, app, jsonify, request, abort, Response

    app = Flask(__name__)

    @app.route('/jsonrpc', methods=['POST'])
    def jrpc():
        payload = request.json
        result = []
        for p in payload if isinstance(payload, list) else [payload]:
            if p.get('jsonrpc') != '2.0': abort(400)
            r = None
            if p.get('method') == 'notify':
                data = p.get('params')
                # process data
                i = p.get('id')
                if i:
                    r = { "jsonrpc": "2.0", "result": { "ok": True }, "id": i}
            else:
                i = p.get('id')
                if i:
                    r = { "jsonrpc": "2.0", "error":
                            { "code": 404, "message": "method not found" },
                            "id": i}
            if not isinstance(payload, list):
                result = r
            else:
                result.append(r)
        if result:
            return jsonify(result)
        else:
            return Response(None, 202)


Basic authentication
--------------------

All HTTP notifiers support basic authentication. To start using it, set
**username** and **password** notifier properties.

.. _bulk_notify:

Bulk (buffered) notifications
=============================

If there are lots of events between nodes, communication channels and
controller processes may be flooded and work unstable.

In this case, it is recommended to use bulk notifications by setting *buf_ttl*
notifier option. E.g. if the option is set to 0.1, events are grouped in the
buffer and sent every 100ms in bulk.

To use bulk notifications with :ref:`MQTT<mqtt_bulk>`, additional options need
to be set.

To use bulk notifications with web sockets (between controllers and with `EVA
JS Framework <https://github.com/alttch/eva-js-framework/>`_, *ws_buf_ttl*
option need to be set in the controller props (on receivers), or in case of
framework, with

.. code:: javascript

    $eva.intrval("ws_buf_ttl", 0.1);

Notifier frame counters
=======================

To monitor load of notifiers, "notifier list" :doc:`CLI </cli>` command or
:ref:`list_notifiers<sysapi_list_notifiers>` API method can be used.

The obtained "frame_counter" value is a frame counter of total packets sent via
the notifier. The counter is unsigned 32-bit integer, which means that after
4,294,967,295 its value is reset to zero.
