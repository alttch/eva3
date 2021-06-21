EVA ICS 3.4.0
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
  supervisorctl (using "service/supervisord-program" registry key field).

- uc-control, lm-control and sfa-control scripts are removed. Consider using
  "eva" or "eva-control" only.

- backups from versions, below 3.4, are INCOMPATIBLE

- plugins and custom deployment tools no longer can manipulate with
  configuration files - these does not exist any longer. Consider switching to
  EVA Registry.

- mailer configuration is now unified for all components.

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

- Automatic converter imports mailer configuration from lm.ini only. If mailer
  configuration is defined elsewhere, import it into the registry manually.

- If updating from a mirror and failed, try removing system-wide
  "python3-cffi-backend" and run the update again.

- Some binary Python modules were switched to Rust. To avoid venv update
  problems, consider installing on Rust manually (all new (3.4+) EVA ICS nodes
  have Rust installed by default, if installed with the automatic installer).

  .. code::
  
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

If registry conversion fails
============================

- Install EVA ICS instance, stop all services except registry

- Put current "runtime" and "etc" folders e.g. to "/tmp/eva-legacy"

- run EVA_DIR/install/convert-legacy-configs --dir /tmp/eva-legacy import

- manually copy runtime/db and custom runtime folders into the new instance

- start all services back
