EVA ICS 3.2.3
*************

What's new
==========

New features:

Complete change log: https://get.eva-ics.com/3.2.3/stable/CHANGELOG.html

Update instructions
===================

* JS SFA Framework is now deprecated. Use [EVA JS
  Framework](https://www.npmjs.com/package/@eva-ics/framework) instead:
 (majority functions are compatible with SFA Framework).

* MQTT server is no longer required if EVA ICS controllers run on a single
  host/network. You may remove MQTT data exchange between controller P2P
  connection by setting *mqtt_update* property to null* (exec *controller prop
  <controller> mqtt_update* command for SFA and LM controllers).

