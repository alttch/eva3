UC UDP API
**********

UC UDP API enables to call API action and update functions by sending a simple
UDP packet.

Basics
======

As there is no feedback in UDP, it is not recommended to use UDP API in cases
where reliability is critical, but its usability for programmable
microcontrollers sometimes takes advantage.

To update the status of the item send the following UDP packet to API port:

    <ID> u <status> [value]

(**ID** - item id, **value** - optional parameter).

To send :ref:`action<ucapi_action>` for the unit send the following UDP packet
to API port:

    <ID> <status> [value] [priority]

(value and priority** optional parameters).

If you needs to skip the parameter, set it to 'None'. For example:

    sensor1 u None 29.55

will keep sensor1 status and set value 29.55;

or

    unit1 1 None 50

will run the action for unit1 for changing its status to 1, without changing
the value, with priority 50.

Batch commands
==============

You can specify multiple commands in one packet separating them with NL (*\n*)
symbol. Example::

    sensor1 u 1 29.55
    sensor2 u 1 26
    sensor3 u 1 38

Encryption and authentication
=============================

You can specify in :ref:`controller configuration<uc_config>` to accept only
encrypted packets from the specified hosts or networks. By default it's
recommended to accept unencrypted packets without authentication only in
trusted networks. The packet is encrypted and signed with API key and can not
be decrypted and used without having it, so API key acts both for encryption
and authentication.

Encrypted packet format is:

    \|KEY_ID\|ENCRYPTED_DATA

Where **KEY_ID** is API key ID and **ENCRYPTED_DATA** - UDP API packet (which
may contain either single or multiple commands at once). The data is encrypted
using `Fernet <https://cryptography.io/en/latest/fernet/>`_ - a symmetric
encryption method which uses 128-bit AES in CBC mode and PKCS7
padding, with HMAC using SHA256 for authentication.

Fernet requires 32-bit base64-encoded key, so before data encryption, API key
should be converted with the following: base64encode(sha256sum(api_key)).

Python example:

.. code-block:: python

    import hashlib
    import base64

    from cryptography.fernet import Fernet

    api_key = 'mysecretapikey'
    data = 'sensor1 u 1 29.55'

    encryption_key = base64.b64encode(hashlib.sha256(api_key.encode()).digest())
    ce = Fernet(encryption_key)

    result = ce.encrypt(data.encode())

Fernet implementation is simple and pre-made libraries are available for all
major programming languages.

Custom packets
==============

You can send a custom packet to let it be parsed by loaded
:doc:`PHI</phi_development>`.

Custom packet format is (\\x = hex):

    \\x01 HANDLER_ID \\x01 DATA

**DATA** is always transmitted to handler in binary format. Encryption,
authentication and batch commands in custom packets are not supported.
