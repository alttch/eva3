Roboger
*******

`Roboger <https://roboger.com/>`_ is a free robots event messaging service,
which can be easily integrated with EVA ICS :doc:`logic control macros
</lm/macros>`.

Servers supported
=================

:doc:`/lm/lm` supports both `roboger.com <https://roboger.com/>`_ and local
**Roboger** server instances.

Setup
=====

Preparing system
----------------

:doc:`/lm/lm` has pre-installed Roboger extension called **rpush**, which uses
local Roboger client configuration settings from
*/usr/local/etc/roboger_push.ini*. The easiest way to create Roboger push
configuration is installing Roboger push CLI:

.. code:: bash

   curl -s https://raw.githubusercontent.com/alttch/roboger/master/bin/install-roboger-push | sudo bash /dev/stdin YOUR_ROBOGER_ADDRESS


Preparing LM extension
----------------------

**rpush** extension requires *pyrpush* module. Append "pyrpush" to **EXTRA**
variable of */opt/eva/etc/venv* and then rebuild EVA ICS venv:

.. code:: bash

   /opt/eva/install/build-venv

Loading LM extension
--------------------

As :doc:`/lm/lm` uses local Roboger push configuration file, no extra
configuration is required. Just type:

.. code:: bash

   eva lm ext load roboger rpush -y

and it's ready to use.

Using in macros
===============

After the extension is loaded, function *roboger_push* becomes available in all
:doc:`logic control macros </lm/macros>`:

.. code:: python

   roboger_push(msg='test error', level='error')

The function parameters are equal to params of `pyrpush.push
<https://pypi.org/project/pyrpush/>`_ function.
