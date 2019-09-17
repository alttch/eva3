Energenie EG-PM2-LAN
********************

`EG-PM2-LAN <https://energenie.com/item.aspx?id=7557>`_ is an affordable smart
power switch solution, which can be integrated with EVA ICS.

Setup
=====

The switch API is pretty slow and it's not recommended to fetch it on every
state update request. To solve this, EG-PM2-LAN EVA PHI module has 2 different
features:

* **cache=N** socket state is cached for N seconds and unit gets cached state
  on updates.

* **update=N** PHI performs :doc:`item </items>` state updates by itself,
  *update_interval* item parameter is not required.

Additionally, PHI module has parameter *skip_logout*, which can be used to skip
logout HTTP call and speed up API even more. Note, that if this parameter is
set, you can not login to switch from another device, except the one
:doc:`/uc/uc` is installed on.

Consider EG-PM2-LAN switch is set up with IP 192.168.1.100 and password 123.
We'll use *update* feature and set *skip_logiut*. Update interval will be set
to 60 seconds, that's more than enough, as only EVA ICS can control the switch
and states may differ only if switch reboot has been occurred.

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/relays/eg_pm2lan.py
   eva uc phi load eg1 eg_pm2lan -c host=192.168.1.100,pw=123,skip_logout=1,update=60 -y
   # create unit for port 1
   eva uc create unit:control/u1 -y
   # assign driver to unit 1
   eva uc driver assign unit:control/u1 eg1.default -c port=1 -y
   # create unit for port 2
   eva uc create unit:control/u2 -y
   # assign driver to unit 2
   eva uc driver assign unit:control/u2 eg1.default -c port=2 -y
   # ... repeat the steps for ports 3 and 4 if required ...
