Amazon Web Services
*******************

AWS IoT as MQTT broker
======================

:ref:`MQTT<mqtt_>` broker is used when EVA ICS controllers are located in
different networks and can not exchange data with P2P connections.

Instead of setting up dedicated MQTT server, you can use cloud-based service,
e.g. AWS IoT.

* Create AWS IoT Core "thing"
* Apply the following policy:

.. code-block:: json

    {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action":["iot:*"],
            "Resource": ["*"]
        }]
    }

During installation
-------------------

Options for EVA ICS :doc:`installation</install>` (*easy-setup*):

* MQTT host: AWS IoT endpoint host (XXXXXXXXX.iot.XXXXXXXXX.amazonaws.com)
* MQTT port: 8883
* MQTT user, password: leave empty
* MQTT space: leave empty
* MQTT SSL: should be enabled (answer 'y' if using *easy-setup*; when notifier
  is configured later, SSL is automatically enabled as soon as *ca_certs*
  property is set)
* MQTT CA file, cert file, key file: provided by AWS (use private key file as
  key file)
* Disable MQTT retain (answer 'y' in *easy-setup*) to make sure no topics with
  retain flag will be sent to MQTT broker (otherwise EVA ICS controller will be
  instantly disconnected)
* Use MQTT QoS *0* or *1* (default)
* It's recommended to create "things" for each EVA ICS controller. After setup,
  MQTT cert file and key file can be changed with CLI (*eva ns
  [controller_type]...*). Don't forget to restart the controller to apply
  notifier configuration.

After installation
------------------

If no MQTT broker is set up, just run *easy-setup* again and follow the
instructions.

If you want to set up additional MQTT broker, let's create new MQTT notifier,
e.g. for :doc:`/lm/lm`:

.. code:: shell

    eva -I
    ns lm
    # create new notifier called e.g. "cmq"
    # replace XXXXXXXXX.iot.XXXXXXXXX.amazonaws.com with your AWS endpoint
    create cmq mqtt:XXXXXXXXX.iot.XXXXXXXXX.amazonaws.com:8883
    # disable MQTT retain - required
    set cmq retain_enabled 0
    # announce controller every 5 seconds
    set cmq announce_interval 5
    # accept API calls
    set cmq api_enabled 1
    # discover other controllers
    set cmq discovery_enabled 1
    # Turn SSL on, set CA file provided by AWS
    set cmq ca_certs /path/to/cafile
    # Set cert and key file, both provided by AWS
    set cmq keyfile /path/to/keyfile
    set cmq certfile /path/to/certfile
    # Test it, should work
    test cmq
    # if it works - subscribe notifier to item states
    subscribe state cmq -g '#'
    # restart controller server
    server restart

Amazon Polly TTS
================

if you want to use Amazon Polly Text-to-Speech engine with EVA ICS, refer to
:doc:`tts` documentation.
