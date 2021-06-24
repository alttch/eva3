Extending HOWTO
***************

There are several different ways to extend EVA ICS functionality, each one is
preferred for certain tasks.

Tips and tricks
===============

* put *development: true* in *server* field of *config/<controller>/main*
  :doc:`registry</registry>` key. This option automatically enables traceback
  logging and debug mode (don't use on production!)

* instead of e.g. *eva uc server start*, run *eva uc server launch* to output
  everything to the system console.

* use debuggers and profilers. We use and recommend *ipdb* and `ppTOP
  <https://pptop.io/>`_.

* don't be surprised that the system performance is much slower, when debug
  mode is enabled.

* EVA ICS uses asyncio only for the internal code. All user scripts and
  extensions are executed in separate threads. So keep your code thread-safe.

* Invent own bus connections only if there is no virtual bus provided.

I/O
===

* :doc:`item_scripts` (:doc:`/uc/uc`) - exchange data with an equipment,
  quickly and dirty 

* :doc:`PHI modules<phi_development>` (:doc:`/uc/uc`) - exchange data with an
  equipment in a proper and fast way 

Logic
=====

* :doc:`corescript` - tiny Python snippets to handle events, quickly and dirty

* :doc:`/lm/macros` (:doc:`/lm/lm`) - tiny scripts to handle event logic or be
  executed on request

* :doc:`/lm/ext` (:doc:`/lm/lm`) - extend functionality of logic macros to
  implement certain features

Plug-ins
========

* :doc:`plugins` - applications and function libraries that run inside EVA ICS.
  This is the most advanced way to extend EVA ICS functionality: plug-ins can
  implement all of the above plus much and much more.


Extensions as packages
======================

See :doc:`/packages`
