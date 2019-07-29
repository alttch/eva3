EVA ICS 3.2.4
*************

What's new
==========

New features:

- InfluxDB and Prometheus integration
- Logging to syslog
- server events
- CLI improvements

Complete change log: https://get.eva-ics.com/3.2.4/stable/CHANGELOG.html

Update instructions
===================

If you use MQTT for controller interconnection, it's recommended to subscribe
notifiers to server events:

```shell
eva -I
ns <uc|lm|sfa>
subscribe server <notifier_id>
```

Note
====

EVA ICS 3.2.4 is the last version with support of Python 3.4. Upgrade Python at
least to 3.5, don't forget to rebuild venv after:

```shell
eva server stop
cd /opt/eva
rm -rf python3
./install/build-venv
```

