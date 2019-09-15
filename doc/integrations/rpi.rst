Raspberry Pi
************

`Raspberry Pi <https://www.raspberrypi.org/>`_ micro-computer, as well as any
clone, home or industrial, can be used to run any of EVA ICS components.

Hardware recommendations
========================

To get max performance and avoid slowdowns, Raspberry Pi 3 or newer model is
highly recommended. It's also recommended to install at least UHS-I Class SD
Card or faster.

Installation
============

Proceed with :doc:`installation </install>`. Note that as soon as Raspbian
Linux is detected, EVA ICS installer script install *pandas* and *cryptography*
Python modules with apt (*pandas* installation is very slow, *cryptography* has
known problems when compiling from source). If your computer uses any Raspbian
clone, which is not detected properly, append *--force-os raspbian* to EVA ICS
installer (run all commands as root):

.. code:: shell

   curl geteva.cc | sudo sh /dev/stdin -a --force-os raspbian

It's also recommended to double-check is UTF-8 locale supported properly and if
no - reconfigure it with

.. code:: shell

   dpkg-reconfigure locales


GPIO
====

Raspberry Pi GPIO can be used with ready-to-use `EVA ICS PHIs
<https://www.eva-ics.com/phi>`_. All GPIO PHIs require *gpiozero* Python
module, so instal it first:

.. code:: shell

   /opt/eva/python3/bin/pip3 install -U gpiozero

There are 3 primary PHIs for GPIO bus:

* **gpio_button** handles GPIO inputs
* **gpio_out** handles GPIO outputs
* **gpio_power** similar to *gpio_out* but sets GPIO OUT to 1 as soon as
  :doc:`/uc/uc` is started (e.g. used to give power to other controlled
  equipment).

Example, let's put a hardware button (or any other input) on GPIO port 20 and
monitor it (you will probably need to run all commands as root, also you may
type *eva uc -I* to start interactive :doc:`/uc/uc` shell):

.. code:: shell

   eva uc phi download https://get.eva-ics.com/phi/gpio/gpio_button.py
   # gpio_buttons PHI module requires all ports to be listed in load config.
   eva uc phi load gbuttons gpio_button -c port=20 -y
   # create button sensor
   eva uc create sensor:buttons/button20 -y
   # assign driver to sensor
   eva uc driver assign sensor:buttons/button20 gbuttons.default -c port=20 -y

That's all. When button is pressed, value of *sensor:buttons/button20* is set
to *1*.
