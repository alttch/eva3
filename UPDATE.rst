EVA ICS 3.4
*************

What's new
==========

- configs and runtime data moved to crash-free YEDB database
- native InfluxDB v2 support
- batch events
- stability and performance improvements

Complete change log: https://get.eva-ics.com/3.4.0/stable/CHANGELOG.html

Removed and deprecated
======================

- Supervisord is no longer supported out-of-the-box. If easy-setup is used to
  configure supervisord, consider writing additional custom configuration
  scripts. "eva-control" still supports controller management with
  supervisorctl (using "service/supervisord-program" field of controller
  configuration key).

- uc-control, lm-control and sfa-control scripts are removed. Consider using
  "eva" or "eva-control" only.

Update instructions
===================

- To use event buffering in UI, update EVA JS Framework to 0.3.23
  
- The update script tries to automatically convert / import the existing
  configs into YEDB, so update process can be longer. DO NOT FORGET BACKUP YOUR
  INSTALLATION BEFORE APPLYING THE UPDATE!

- If update is executed under root and systemd is used, an additional
  eva-ics.service is installed automatically. Otherwise, manually add
  "EVA_DIR/sbin/registry-control start" to the system startup. The registry
  service MUST be started before the primary EVA ICS service.

- The EVA ICS registry service MUST be always online. If service shutdown is
  required, shutdown all EVA ICS components first.
