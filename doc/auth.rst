Authentication
**************

.. contents::

API keys
========

Default and custom API keys
---------------------------

API keys are the primary entities of EVA ICS authentication and access control
checking.

After the installation, the following API keys are created automatically:

* **masterkey** the primary (super) key with the unlimited access to any
  resource. At least one master key always must be present in the controller
  configuration.

* **default** the default key for controller inter-connections. Has an access
  to all :doc:`items<items>`, no access to system and master functions and has
  *allow=cmd,[device]*

* **operator** the default user key. Similar to the "default" key, but with
  *allow=lock*

Custom API keys can be created either in the controller key configuration
in :doc:`/registry` (static, requires controller restart on changes), with
:doc:`/sysapi` key management functions or with :doc:`command-line interface
</cli>` (dynamic, stored either in "db" or in "userdb"). Master keys can be
created only in the registry.

The default master key (with id *masterkey*) can be changed for all installed
components in bulk, using *eva masterkey* CLI command.

.. note::

    Each EVA ICS component has its own key pack, even if all components are
    running under the same installation. Sharing API keys configurations and/or
    database is not recommended.
    
    To speed up API responses, all API keys are loaded and cached during the
    controller startup.

API key properties and ACL
--------------------------

The current ACL can be obtained with "test" API/CLI command. Key properties can
be modified with :doc:`/sysapi` key management functions or with
:doc:`command-line interface</cli>`. "Static" keys, defined in the registry,
can not be re-configured dynamically.

API key properties:

* **allow** the key allow list:

    * **cmd** access to remote command call functions
    * **lock** access to lock management functions
    * **device** (for :doc:`/uc/uc` only) access to device templates functions

* **cdata** list of custom data. Can be set to any custom values (up to 16384
  characters), appears in serialized ACL as-is. The field is a list. If set
  from a string, it is automatically split with commas.

* **dynamic** read-only value, which shows is the key "dynamic" (True, stored
  in the db) or "static" (False, defined in the :doc:`registry</registry>`).

* **groups** comma-separated item groups the key has the access to (despite of
  item types). MQTT-style wildcards ('#', '+') are allowed (e.g. "#" = access
  to the all items).

* **groups_deny** comma-separated item groups the key has forbidden access to
  (e.g. a wildcard is used in *groups* but some groups are excluded from ACL).
  The key still has read-only access if allowed with other ACL properties.

* **groups_ro** same as *groups* but for read-only access.

* **hosts_allow** comma-separated list of hosts/networks the key has the access
  from.

* **hosts_assign** comma-separated list of hosts/networks to automatically set
  the key for any non-authenticated API requests.

* **id** the key ID, unique.

* **items**, **items_ro** same as groups, but grants an access to the specified
  items. Wildcards are not allowed.

* **items_deny** same as *groups_deny* but for individual items.

* **key** the key itself (up to 64 characters). Filled with 32 random chars
  automatically after creation.

* **master** key is the master key if set to True

* **pvt**, **rpvt** comma-separated lists for :doc:`SFA PVT/RPVT
  </sfa/sfa_pvt>` ACLs.

Users
=====

Unlike the typical approach, when a user is the primary authentication entity
and can have one or multiple API keys, EVA ICS authentication works in the
opposite way: API keys are the primary entities and there could be one or more
users linked to the each one. Consider, for the users, API keys act as ACL
groups.

The approach may look unusual, but there is a strong reason to work this way:
all external resources (EVA ICS controller inter-connections, 3rd party
apps) should always use API keys only, while user accounts are generally used
only for authentication via web-interfaces. Majority of EVA ICS installations
have no user accounts at all, while all setups require API keys for control and
management.

When such approach is used, there is also no reason to have "service" user
accounts for the service functions.

Users can be created with :doc:`/sysapi` user management functions or with
:doc:`command-line interface </cli>`.

API calls can not be performed with user accounts directly, the users must
login and obtain :doc:`api_tokens`.

.. _combined_acl:

Combined ACLs
=============

As API keys are used as user ACLs, a user can have more than one API key
assigned locally or with :doc:`Active Directory<msad>` groups.

If more than one key (so more than one ACL) is assigned:

* item ACLs, cdata and allow/assign hosts/networks are merged as-is, including
  deny ACLs

* special ACLs are merged basing on a higher access level (e.g. if one of keys
  has master access, the combined ACL will have master access as well)

* to assign multiple API keys to a local user, separate them either with commas
  (in :doc:`CLI </cli>`) or send as list (:ref:`create_user
  <sysapi_create_user>` API function).

* **key id** in reports and :ref:`test <sysapi_test>` API function has the value
  "comb:KEY_1+KEY_2+...KEY_N"

* the key gets an additional field **combined_from** which contains a list of
  key ids the ACLs are combined from.

Only authenticated users can have combined access. Combined API keys are
generated for internal purposes only and there is no way to obtain them for
direct API requests (use users' session tokens instead).
